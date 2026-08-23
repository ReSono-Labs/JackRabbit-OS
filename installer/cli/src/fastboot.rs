use crate::command::CommandError;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::thread;
use std::time::{Duration, Instant};

pub trait Fastboot {
    fn execute(&mut self, arguments: &[String]) -> Result<String, CommandError>;
}

pub struct NativeFastboot {
    executable: PathBuf,
    serial: Option<String>,
}

impl NativeFastboot {
    pub fn discover(release_root: &Path) -> Result<Self, CommandError> {
        let configured = std::env::var_os("JACKRABBIT_FASTBOOT").map(PathBuf::from);
        let bundled = if cfg!(windows) {
            release_root.join("tools/fastboot.exe")
        } else {
            release_root.join("tools/fastboot")
        };
        let executable = if let Some(configured) = configured {
            if !configured.is_file() {
                return Err(CommandError::new(
                    "JR-CLI-FASTBOOT-MISSING",
                    format!(
                        "configured packaged fastboot is missing: {}",
                        configured.display()
                    ),
                ));
            }
            configured
        } else if bundled.is_file() {
            bundled
        } else {
            PathBuf::from(if cfg!(windows) {
                "fastboot.exe"
            } else {
                "fastboot"
            })
        };
        Ok(Self {
            executable,
            serial: None,
        })
    }

    pub fn bind_one(&mut self) -> Result<String, CommandError> {
        self.try_bind_one()?.ok_or_else(|| {
            CommandError::new(
                "JR-CLI-DEVICE-COUNT",
                "connect exactly one R1 in FASTBOOT; found 0",
            )
        })
    }

    pub fn try_bind_one(&mut self) -> Result<Option<String>, CommandError> {
        let output = self.execute(&["devices".into()])?;
        if output.contains("no permissions") {
            return Err(permission_error());
        }
        let devices: Vec<_> = output
            .lines()
            .filter_map(|line| {
                let mut fields = line.split_whitespace();
                let serial = fields.next()?;
                let mode = fields.next()?;
                matches!(mode, "fastboot" | "fastbootd").then_some(serial.to_string())
            })
            .collect();
        if devices.len() > 1 {
            return Err(CommandError::new(
                "JR-CLI-DEVICE-COUNT",
                format!(
                    "connect exactly one R1 in FASTBOOT; found {}",
                    devices.len()
                ),
            ));
        }
        let selected = devices.into_iter().next();
        self.serial = selected.clone();
        Ok(selected)
    }

    pub fn wait_for_mode(&mut self, expected_userspace: bool) -> Result<(), CommandError> {
        let deadline = Instant::now() + Duration::from_secs(90);
        loop {
            match self.bind_one().and_then(|_| self.getvar("is-userspace")) {
                Ok(value) if value == if expected_userspace { "yes" } else { "no" } => {
                    return Ok(())
                }
                Err(error) if error.code() == "JR-CLI-USB-PERMISSION" => return Err(error),
                _ if Instant::now() < deadline => thread::sleep(Duration::from_millis(500)),
                _ => {
                    return Err(CommandError::new(
                        "JR-CLI-MODE-TIMEOUT",
                        "R1 did not reconnect in the expected fastboot mode within 90 seconds",
                    ))
                }
            }
        }
    }

    pub fn getvar(&mut self, name: &str) -> Result<String, CommandError> {
        let output = self.execute(&["getvar".into(), name.into()])?;
        output
            .lines()
            .find_map(|line| {
                line.trim()
                    .strip_prefix(&format!("{name}: "))
                    .map(str::to_string)
            })
            .ok_or_else(|| {
                CommandError::new("JR-CLI-FASTBOOT-VALUE", format!("R1 did not return {name}"))
            })
    }

    pub fn command(&mut self, arguments: &[&str]) -> Result<(), CommandError> {
        self.execute(
            &arguments
                .iter()
                .map(|value| value.to_string())
                .collect::<Vec<_>>(),
        )
        .map(|_| ())
    }
}

impl Fastboot for NativeFastboot {
    fn execute(&mut self, arguments: &[String]) -> Result<String, CommandError> {
        let mut command = Command::new(&self.executable);
        if arguments.first().map(String::as_str) != Some("devices") {
            if let Some(serial) = &self.serial {
                command.arg("-s").arg(serial);
            }
        }
        command.args(arguments);
        let output = command.output().map_err(|error| {
            CommandError::new(
                "JR-CLI-FASTBOOT-MISSING",
                format!("cannot run {}: {error}", self.executable.display()),
            )
        })?;
        let text = format!(
            "{}{}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );
        if fastboot_failed(output.status.success(), &text) {
            if text.contains("no permissions") {
                return Err(permission_error());
            }
            return Err(CommandError::new("JR-CLI-FASTBOOT-FAILED", text.trim()));
        }
        Ok(text)
    }
}

fn fastboot_failed(process_succeeded: bool, output: &str) -> bool {
    !process_succeeded || output.lines().any(|line| line.contains("FAILED"))
}

fn permission_error() -> CommandError {
    CommandError::new("JR-CLI-USB-PERMISSION", "Linux denied the R1 USB node. Run the package's install.sh so it can install drivers/51-jackrabbit-r1.rules, reconnect the R1, and retry. fastbootd uses 18d1:4ee0.")
}

#[cfg(test)]
mod tests {
    use super::fastboot_failed;

    #[test]
    fn remote_failure_fails_even_when_fastboot_exits_zero() {
        assert!(fastboot_failed(
            true,
            "getvar:x FAILED (remote: 'Could not open partition')"
        ));
        assert!(fastboot_failed(false, "fastboot: error"));
        assert!(!fastboot_failed(
            true,
            "product: k65v1_64_bsp\nFinished. Total time: 0.001s"
        ));
    }
}
