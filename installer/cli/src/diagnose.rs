use crate::command::CommandError;
use fastboot_protocol::nusb::{devices, NusbFastBoot};
use futures::executor::block_on;
use std::sync::mpsc;
use std::thread;
use std::time::Duration;

const R1_VENDOR_ID: u16 = 0x0e8d;
const R1_FASTBOOT_PRODUCT_ID: u16 = 0x201c;
const VARIABLES: [&str; 6] = [
    "product",
    "serialno",
    "unlocked",
    "current-slot",
    "is-userspace",
    "max-download-size",
];

struct Snapshot {
    product: String,
    unlocked: bool,
    current_slot: String,
    userspace: bool,
    max_download_size: u64,
}

pub fn run() -> Result<(), CommandError> {
    println!("Read-only R1 diagnostic");
    println!(
        "Confirm the R1 screen says FASTBOOT and connect exactly one device. No partition will be written.\n"
    );

    let (sender, receiver) = mpsc::channel();
    thread::spawn(move || {
        let _ = sender.send(block_on(read_snapshot()));
    });
    let snapshot = receiver
        .recv_timeout(Duration::from_secs(10))
        .map_err(|_| {
            CommandError::new(
                "JR-CLI-FASTBOOT-TIMEOUT",
                "the fixed read-only USB diagnostic timed out",
            )
        })??;

    println!("Product: {}", snapshot.product);
    println!(
        "Mode: {}",
        if snapshot.userspace {
            "fastbootd"
        } else {
            "bootloader"
        }
    );
    println!("Current slot: {}", snapshot.current_slot);
    println!(
        "Bootloader unlocked: {}",
        if snapshot.unlocked { "yes" } else { "no" }
    );
    println!("Maximum download: {} bytes", snapshot.max_download_size);
    println!("Device serial: redacted");
    println!(
        "\nRead-only diagnostic complete. No public install profile is enabled in this build."
    );
    Ok(())
}

async fn read_snapshot() -> Result<Snapshot, CommandError> {
    let candidates: Vec<_> = devices()
        .await
        .map_err(|_| usb_error())?
        .filter(|device| {
            device.vendor_id() == R1_VENDOR_ID && device.product_id() == R1_FASTBOOT_PRODUCT_ID
        })
        .collect();
    match candidates.len() {
        0 => {
            return Err(CommandError::new(
                "JR-CLI-DEVICE-MISSING",
                "no exact R1 fastboot USB device is visible; check the screen, cable, driver, or USB permissions",
            ))
        }
        1 => {}
        _ => {
            return Err(CommandError::new(
                "JR-CLI-DEVICE-MULTIPLE",
                "more than one exact R1 fastboot USB device is visible; disconnect every R1 except the intended device",
            ))
        }
    }

    let mut transport = NusbFastBoot::from_info(&candidates[0])
        .await
        .map_err(|_| usb_error())?;
    let mut values = Vec::new();
    for variable in VARIABLES {
        let value = transport.get_var(variable).await.map_err(|_| {
            CommandError::new(
                "JR-CLI-FASTBOOT-REJECTED",
                "the R1 rejected a fixed read-only identity query",
            )
        })?;
        if variable != "serialno" {
            values.push((variable, value));
        }
    }

    snapshot_from_values(&values)
}

fn snapshot_from_values(values: &[(&str, String)]) -> Result<Snapshot, CommandError> {
    let value = |name: &str| {
        values
            .iter()
            .find(|(key, _)| *key == name)
            .map(|(_, value)| value.as_str())
            .unwrap_or("")
    };
    let unlocked = parse_yes_no(value("unlocked"))?;
    let userspace = parse_yes_no(value("is-userspace"))?;
    let current_slot = value("current-slot");
    if !matches!(current_slot, "a" | "b") {
        return Err(fastboot_value_error());
    }
    let product = value("product");
    if product.is_empty() || product.len() > 64 {
        return Err(fastboot_value_error());
    }
    let max_download_size =
        parse_hex_size(value("max-download-size")).ok_or_else(fastboot_value_error)?;

    Ok(Snapshot {
        product: product.to_string(),
        unlocked,
        current_slot: current_slot.to_string(),
        userspace,
        max_download_size,
    })
}

fn parse_yes_no(value: &str) -> Result<bool, CommandError> {
    match value {
        "yes" => Ok(true),
        "no" => Ok(false),
        _ => Err(fastboot_value_error()),
    }
}

fn parse_hex_size(value: &str) -> Option<u64> {
    let digits = value.strip_prefix("0x")?;
    u64::from_str_radix(digits, 16)
        .ok()
        .filter(|size| *size > 0)
}

fn usb_error() -> CommandError {
    CommandError::new(
        "JR-CLI-USB",
        "the operating system denied or failed the exact R1 USB connection",
    )
}

fn fastboot_value_error() -> CommandError {
    CommandError::new(
        "JR-CLI-FASTBOOT-VALUE",
        "the R1 returned an unsupported read-only identity value",
    )
}

#[cfg(test)]
mod tests {
    use super::{parse_hex_size, snapshot_from_values, VARIABLES};

    fn values() -> Vec<(&'static str, String)> {
        vec![
            ("product", "rabbit-r1".into()),
            ("unlocked", "yes".into()),
            ("current-slot", "a".into()),
            ("is-userspace", "no".into()),
            ("max-download-size", "0x10000000".into()),
        ]
    }

    #[test]
    fn command_set_is_fixed_and_read_only() {
        assert_eq!(
            VARIABLES,
            [
                "product",
                "serialno",
                "unlocked",
                "current-slot",
                "is-userspace",
                "max-download-size"
            ]
        );
        let source = include_str!("diagnose.rs");
        let production = source.split("#[cfg(test)]").next().unwrap();
        for forbidden in [".flash(", ".erase(", ".reboot(", ".download("] {
            assert!(!production.contains(forbidden));
        }
    }

    #[test]
    fn creates_redacted_typed_snapshot_from_fixed_values() {
        let snapshot = snapshot_from_values(&values()).unwrap();
        assert_eq!(snapshot.product, "rabbit-r1");
        assert!(snapshot.unlocked);
        assert_eq!(snapshot.current_slot, "a");
        assert!(!snapshot.userspace);
        assert_eq!(snapshot.max_download_size, 268_435_456);
    }

    #[test]
    fn rejects_malformed_machine_values() {
        for (name, bad) in [
            ("unlocked", "true"),
            ("current-slot", "c"),
            ("is-userspace", "false"),
            ("max-download-size", "10000000"),
        ] {
            let mut changed = values();
            changed.iter_mut().find(|(key, _)| *key == name).unwrap().1 = bad.into();
            assert!(snapshot_from_values(&changed).is_err());
        }
    }

    #[test]
    fn accepts_only_positive_prefixed_hex_sizes() {
        assert_eq!(parse_hex_size("0x10000000"), Some(268_435_456));
        assert_eq!(parse_hex_size("10000000"), None);
        assert_eq!(parse_hex_size("0x0"), None);
        assert_eq!(parse_hex_size("not-hex"), None);
    }
}
