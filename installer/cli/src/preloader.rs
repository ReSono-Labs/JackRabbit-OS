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
    match candidates {
        [] => Ok(None),
        [only] => Ok(Some(only)),
        _ => Err(CommandError::new(
            "JR-CLI-PRELOADER-COUNT",
            "more than one exact R1 preloader device appeared; disconnect every R1 and retry with one device",
        )),
    }
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
}
