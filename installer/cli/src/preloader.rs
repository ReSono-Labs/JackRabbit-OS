use crate::command::CommandError;
use serialport::SerialPortType;
use std::io::Write;
use std::time::Duration;

const R1_PRELOADER_VENDOR: u16 = 0x0e8d;
const R1_PRELOADER_PRODUCT: u16 = 0x2000;
const FASTBOOT_PAYLOAD: &[u8; 8] = b"FASTBOOT";

pub fn try_enter() -> Result<bool, CommandError> {
    let ports = serialport::available_ports().map_err(|error| {
        CommandError::new(
            "JR-CLI-PRELOADER-ENUMERATE",
            format!("cannot enumerate serial devices: {error}"),
        )
    })?;
    let candidates: Vec<_> = ports
        .into_iter()
        .filter_map(|port| match port.port_type {
            SerialPortType::UsbPort(info)
                if info.vid == R1_PRELOADER_VENDOR && info.pid == R1_PRELOADER_PRODUCT =>
            {
                Some(port.port_name)
            }
            _ => None,
        })
        .collect();
    match select_exact(&candidates)? {
        Some(path) => {
            let mut port = serialport::new(path, 115_200)
                .timeout(Duration::from_secs(3))
                .open()
                .map_err(|error| {
                    CommandError::new(
                        "JR-CLI-PRELOADER-OPEN",
                        format!("cannot open the exact R1 preloader port: {error}"),
                    )
                })?;
            port.write_all(FASTBOOT_PAYLOAD).map_err(|error| {
                CommandError::new(
                    "JR-CLI-PRELOADER-WRITE",
                    format!("cannot send the R1 FASTBOOT entry command: {error}"),
                )
            })?;
            println!("FASTBOOT entry command sent. Waiting for the R1 FASTBOOT screen…");
            Ok(true)
        }
        None => Ok(false),
    }
}

fn select_exact(candidates: &[String]) -> Result<Option<&str>, CommandError> {
    let distinct = dedupe_logical(candidates);
    match distinct.as_slice() {
        [] => Ok(None),
        [only] => Ok(Some(only)),
        _ => Err(CommandError::new(
            "JR-CLI-PRELOADER-COUNT",
            format!(
                "more than one exact R1 preloader device appeared ({}); disconnect every R1 and retry with one device",
                distinct.len()
            ),
        )),
    }
}

/// Collapse macOS `tty.*`/`cu.*` device-node pairs for the same physical serial
/// line into a single logical device. A USB CDC preloader registers both
/// `/dev/cu.usbmodemNNN` and `/dev/tty.usbmodemNNN`; they are one R1, not two.
/// Truly distinct devices keep distinct names and still count separately.
fn dedupe_logical<'a>(candidates: &'a [String]) -> Vec<&'a str> {
    let mut distinct: Vec<&'a str> = Vec::new();
    for candidate in candidates {
        let key = logical_device_key(candidate);
        if !distinct
            .iter()
            .any(|existing| logical_device_key(existing) == key)
        {
            distinct.push(candidate);
        }
    }
    distinct
}

fn logical_device_key(path: &str) -> &str {
    let name = path.rsplit('/').next().unwrap_or(path);
    name.strip_prefix("cu.")
        .or_else(|| name.strip_prefix("tty."))
        .unwrap_or(name)
}

#[cfg(test)]
mod tests {
    use super::{select_exact, FASTBOOT_PAYLOAD, R1_PRELOADER_PRODUCT, R1_PRELOADER_VENDOR};

    #[test]
    fn entry_identity_and_payload_are_closed() {
        assert_eq!(
            (R1_PRELOADER_VENDOR, R1_PRELOADER_PRODUCT),
            (0x0e8d, 0x2000)
        );
        assert_eq!(FASTBOOT_PAYLOAD, b"FASTBOOT");
        assert_eq!(select_exact(&[]).unwrap(), None);
        assert_eq!(select_exact(&["r1".into()]).unwrap(), Some("r1"));
        assert!(select_exact(&["one".into(), "two".into()]).is_err());
    }

    #[test]
    fn macos_tty_cu_pair_is_one_logical_device() {
        // Regression: a single R1 registers both /dev/cu.usbmodem31201 and
        // /dev/tty.usbmodem31201 on macOS; the installer must treat them as one R1.
        let candidates = [
            "/dev/cu.usbmodem31201".to_string(),
            "/dev/tty.usbmodem31201".to_string(),
        ];
        let result = select_exact(&candidates).unwrap();
        assert_eq!(result, Some("/dev/cu.usbmodem31201"));
    }

    #[test]
    fn two_distinct_devices_still_fail() {
        // Two genuinely different R1s must still be rejected.
        let candidates = [
            "/dev/cu.usbmodem31201".to_string(),
            "/dev/cu.usbmodem31202".to_string(),
        ];
        let error = select_exact(&candidates).unwrap_err();
        assert_eq!(error.code(), "JR-CLI-PRELOADER-COUNT");
    }
}
