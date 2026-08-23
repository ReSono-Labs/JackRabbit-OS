use crate::{diagnose, install, physical, prompt};
use std::fmt::{Display, Formatter};
use std::io::{self, BufRead, IsTerminal, Write};
use std::path::PathBuf;

#[derive(Debug, PartialEq)]
pub enum Command {
    Help,
    Version,
    Prepare,
    Diagnose,
    Install(PathBuf),
}

#[derive(Debug)]
pub struct CommandError {
    code: &'static str,
    message: String,
}

impl CommandError {
    pub fn new(code: &'static str, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
        }
    }

    pub fn code(&self) -> &'static str {
        self.code
    }
}

impl Display for CommandError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl Command {
    pub fn from_args(mut args: impl Iterator<Item = String>) -> Result<Self, CommandError> {
        match args.next().as_deref() {
            Some("version") => exact(Self::Version, args),
            Some("prepare") => exact(Self::Prepare, args),
            Some("diagnose") => exact(Self::Diagnose, args),
            Some("install") => one_path(args),
            Some("help") | Some("--help") | Some("-h") => exact(Self::Help, args),
            Some(command) => Err(CommandError::new(
                "JR-CLI-COMMAND",
                format!("unsupported command: {command}"),
            )),
            None if io::stdin().is_terminal() => interactive_command(),
            None => Err(CommandError::new(
                "JR-CLI-COMMAND",
                "choose install, prepare, diagnose, or version",
            )),
        }
    }

    pub fn run(self) -> Result<(), CommandError> {
        match self {
            Self::Help => {
                print_help();
                Ok(())
            }
            Self::Version => {
                println!("JackRabbit installer CLI {}", env!("CARGO_PKG_VERSION"));
                Ok(())
            }
            Self::Prepare => physical::run(&mut io::stdin().lock(), &mut io::stdout().lock(), None),
            Self::Diagnose => diagnose::run(),
            Self::Install(release_root) => install::run(&release_root),
        }
    }
}

fn one_path(mut remainder: impl Iterator<Item = String>) -> Result<Command, CommandError> {
    let path = remainder.next().ok_or_else(|| {
        CommandError::new(
            "JR-CLI-ARGUMENT",
            "install requires one extracted release directory",
        )
    })?;
    if remainder.next().is_some() {
        return Err(CommandError::new(
            "JR-CLI-ARGUMENT",
            "install accepts exactly one release directory",
        ));
    }
    Ok(Command::Install(PathBuf::from(path)))
}

fn exact(
    command: Command,
    mut remainder: impl Iterator<Item = String>,
) -> Result<Command, CommandError> {
    if remainder.next().is_some() {
        return Err(CommandError::new(
            "JR-CLI-ARGUMENT",
            "this command accepts no arguments",
        ));
    }
    Ok(command)
}

fn interactive_command() -> Result<Command, CommandError> {
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    loop {
        writeln!(output, "JackRabbit installer").map_err(terminal_io)?;
        writeln!(output, "1. Install JackRabbit from this package").map_err(terminal_io)?;
        writeln!(output, "2. Prepare the R1").map_err(terminal_io)?;
        writeln!(output, "3. Diagnose an R1 already showing FASTBOOT").map_err(terminal_io)?;
        writeln!(output, "4. Show version").map_err(terminal_io)?;
        write!(output, "Choose 1-4: ").map_err(terminal_io)?;
        output.flush().map_err(terminal_io)?;
        let mut answer = String::new();
        input.read_line(&mut answer).map_err(terminal_io)?;
        match answer.trim() {
            "1" => loop {
                write!(output, "Release directory: ").map_err(terminal_io)?;
                output.flush().map_err(terminal_io)?;
                let mut path = String::new();
                input.read_line(&mut path).map_err(terminal_io)?;
                if !path.trim().is_empty() {
                    return Ok(Command::Install(PathBuf::from(path.trim())));
                }
                prompt::incorrect_then_retry_or_cancel(
                    &mut input,
                    &mut output,
                    "cancelled before selecting a release directory",
                )?;
            },
            "2" => return Ok(Command::Prepare),
            "3" => return Ok(Command::Diagnose),
            "4" => return Ok(Command::Version),
            _ => {
                prompt::incorrect_then_retry_or_cancel(
                    &mut input,
                    &mut output,
                    "cancelled before choosing an installer action",
                )?;
                writeln!(output).map_err(terminal_io)?;
            }
        }
    }
}

fn terminal_io(error: io::Error) -> CommandError {
    CommandError::new("JR-CLI-IO", error.to_string())
}

fn print_help() {
    println!("JackRabbit installer fallback\n\nCommands:\n  install RELEASE_DIRECTORY  Verify and install the complete current stock-R1 release\n  prepare                    Guide physical preparation\n  diagnose                   Read fixed R1 fastboot identity and state\n  version                    Show source/package version\n\nRun with no arguments for the prompt-based menu.");
}

#[cfg(test)]
mod tests {
    use super::Command;

    #[test]
    fn accepts_only_exact_closed_commands() {
        assert_eq!(
            Command::from_args(["version".to_string()].into_iter()).unwrap(),
            Command::Version
        );
        assert!(
            Command::from_args(["diagnose".to_string(), "extra".to_string()].into_iter()).is_err()
        );
        assert!(matches!(
            Command::from_args(["install".to_string(), "release".to_string()].into_iter()).unwrap(),
            Command::Install(_)
        ));
        assert!(Command::from_args(["flash".to_string()].into_iter()).is_err());
    }
}
