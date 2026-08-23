use crate::command::CommandError;
use crate::fastboot::{Fastboot, NativeFastboot};
use crate::{physical, preloader, prompt, release};
use std::io::{self, BufRead, Write};
use std::path::Path;
use std::thread;
use std::time::{Duration, Instant};

const SYSTEM_EXT_SIZE: &str = "559304704";

pub fn run(release_root: &Path) -> Result<(), CommandError> {
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    writeln!(output, "JackRabbit guided stock-R1 install\n").map_err(io_error)?;
    release::verify(release_root, |index, artifact| {
        let _ = writeln!(output, "Verifying {}/12: {}", index + 1, artifact.path);
    })?;
    writeln!(output, "Release verified: {}\n", release::RELEASE_ID).map_err(io_error)?;

    let mut fastboot = NativeFastboot::discover(release_root)?;
    let detected_unlocked = match fastboot.try_bind_one()? {
        None => None,
        Some(_) => Some(normalize_connected_fastboot(
            &mut fastboot,
            &mut input,
            &mut output,
        )?),
    };
    physical::run(&mut input, &mut output, detected_unlocked)?;
    if detected_unlocked.is_none() {
        enter_or_find_fastboot(&mut fastboot, &mut input, &mut output)?;
    }
    writeln!(output, "R1 found. Verifying bootloader FASTBOOT…").map_err(io_error)?;
    require_gate(&mut fastboot, false, false)?;

    if fastboot.getvar("unlocked")? == "no" {
        writeln!(output, "The bootloader is locked. Rabbithole Developer → Device modification → Unlock must be enabled.").map_err(io_error)?;
        confirm(
            &mut input,
            &mut output,
            "Unlocking erases all R1 data.",
            "ERASE AND UNLOCK R1",
        )?;
        writeln!(
            output,
            "Watch the R1 screen and follow its unlock confirmation instructions. The installer will wait."
        )
        .map_err(io_error)?;
        fastboot.command(&["flashing", "unlock"])?;
        writeln!(
            output,
            "If the R1 shows another critical-unlock confirmation, follow its on-screen instructions."
        )
        .map_err(io_error)?;
        fastboot.command(&["flashing", "unlock_critical"])?;
        if fastboot.getvar("unlocked")? != "yes" {
            return Err(CommandError::new(
                "JR-CLI-UNLOCK",
                "unlock commands completed but the R1 still reports locked",
            ));
        }
        writeln!(
            output,
            "Unlock verified. Continuing in the same install flow.\n"
        )
        .map_err(io_error)?;
    }

    confirm(
        &mut input,
        &mut output,
        "This installs the complete current JackRabbit image and erases stock user data.",
        "INSTALL JACKRABBIT",
    )?;
    let file = |relative: &str| release::path(release_root, relative).display().to_string();
    let mut step = 1;

    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Writing boot slot A",
        &["flash", "boot_a", &file("images/stock/boot.img")],
    )?;
    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Writing boot slot B",
        &["flash", "boot_b", &file("images/stock/boot.img")],
    )?;
    for slot in ["a", "b"] {
        perform(
            &mut output,
            &mut fastboot,
            &mut step,
            &format!("Writing stock VBMeta slot {}", slot.to_uppercase()),
            &vbmeta_arguments(&format!("vbmeta_{slot}"), &file("images/stock/vbmeta.img")),
        )?;
        perform(
            &mut output,
            &mut fastboot,
            &mut step,
            &format!("Writing stock system VBMeta slot {}", slot.to_uppercase()),
            &vbmeta_arguments(
                &format!("vbmeta_system_{slot}"),
                &file("images/stock/vbmeta_system.img"),
            ),
        )?;
        perform(
            &mut output,
            &mut fastboot,
            &mut step,
            &format!("Writing stock vendor VBMeta slot {}", slot.to_uppercase()),
            &vbmeta_arguments(
                &format!("vbmeta_vendor_{slot}"),
                &file("images/stock/vbmeta_vendor.img"),
            ),
        )?;
    }
    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Entering fastbootd",
        &["reboot", "fastboot"],
    )?;
    writeln!(
        output,
        "The R1 changes USB identity in fastbootd. Linux may require the packaged udev rule."
    )
    .map_err(io_error)?;
    wait_for_mode(&mut fastboot, true, &mut input, &mut output)?;
    require_gate(&mut fastboot, true, true)?;

    writeln!(output, "[10/22] Writing stock super. The R1 screen may go blank. Do not unplug it; follow this terminal.").map_err(io_error)?;
    fastboot.command(&["flash", "super", &file("images/stock/super.img")])?;
    step = 11;

    let partition_probe =
        fastboot.execute(&["getvar".into(), "partition-size:system_ext_a".into()]);
    match partition_probe {
        Ok(output_text) if missing_system_ext(&output_text) => perform(
            &mut output,
            &mut fastboot,
            &mut step,
            "Creating CipherOS system_ext_a",
            &["create-logical-partition", "system_ext_a", SYSTEM_EXT_SIZE],
        )?,
        Err(error) if missing_system_ext(&error.to_string()) => perform(
            &mut output,
            &mut fastboot,
            &mut step,
            "Creating CipherOS system_ext_a",
            &["create-logical-partition", "system_ext_a", SYSTEM_EXT_SIZE],
        )?,
        Ok(output_text) if system_ext_size(&output_text) == Some(559_304_704) => {
            step += 1;
        }
        Ok(_) => {
            return Err(CommandError::new(
                "JR-CLI-SYSTEM-EXT",
                "system_ext_a has an unexpected existing layout",
            ))
        }
        Err(error) => return Err(error),
    }

    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Writing current JackRabbit system",
        &["flash", "system_a", &file("images/jackrabbit/system.img")],
    )?;
    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Writing CipherOS system extensions",
        &[
            "flash",
            "system_ext_a",
            &file("images/cipheros/system_ext.img"),
        ],
    )?;
    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Writing current JackRabbit product",
        &["flash", "product_a", &file("images/jackrabbit/product.img")],
    )?;
    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Writing CipherOS vendor",
        &["flash", "vendor_a", &file("images/cipheros/vendor.img")],
    )?;
    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Returning to bootloader FASTBOOT",
        &["reboot", "bootloader"],
    )?;
    wait_for_mode(&mut fastboot, false, &mut input, &mut output)?;
    require_gate(&mut fastboot, false, true)?;

    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Activating CipherOS VBMeta",
        &vbmeta_arguments("vbmeta_a", &file("images/cipheros/vbmeta.img")),
    )?;
    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Activating CipherOS system VBMeta",
        &vbmeta_arguments(
            "vbmeta_system_a",
            &file("images/cipheros/vbmeta_system.img"),
        ),
    )?;
    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Activating CipherOS vendor VBMeta",
        &vbmeta_arguments(
            "vbmeta_vendor_a",
            &file("images/cipheros/vbmeta_vendor.img"),
        ),
    )?;
    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Erasing stock userdata",
        &["erase", "userdata"],
    )?;
    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Selecting slot A",
        &["set_active", "a"],
    )?;
    perform(
        &mut output,
        &mut fastboot,
        &mut step,
        "Rebooting into JackRabbit",
        &["reboot"],
    )?;
    writeln!(output, "\nImage transfer complete. The screen may remain blank during early first boot. Keep the R1 powered and wait for JackRabbit.").map_err(io_error)
}

fn enter_or_find_fastboot(
    fastboot: &mut NativeFastboot,
    input: &mut impl BufRead,
    output: &mut impl Write,
) -> Result<(), CommandError> {
    writeln!(output, "Waiting up to 60 seconds for the R1.").map_err(io_error)?;
    writeln!(output, "Connect it now. The installer accepts either an R1 already showing FASTBOOT or the powered-off R1 preloader.").map_err(io_error)?;
    let deadline = Instant::now() + Duration::from_secs(60);
    loop {
        if preloader::try_enter()? {
            return wait_for_mode(fastboot, false, input, output);
        }
        if fastboot.try_bind_one()?.is_some() {
            normalize_connected_fastboot(fastboot, input, output)?;
            return Ok(());
        }
        if Instant::now() >= deadline {
            return Err(CommandError::new(
                "JR-CLI-FASTBOOT-ENTRY-TIMEOUT",
                "no R1 appeared as bootloader FASTBOOT, fastbootd, or the exact 0e8d:2000 preloader within 60 seconds",
            ));
        }
        thread::sleep(Duration::from_millis(200));
    }
}

fn normalize_connected_fastboot(
    fastboot: &mut NativeFastboot,
    input: &mut impl BufRead,
    output: &mut impl Write,
) -> Result<bool, CommandError> {
    if fastboot.getvar("is-userspace")? == "yes" {
        require_gate(fastboot, true, false)?;
        fastboot.command(&["reboot", "bootloader"])?;
        wait_for_mode(fastboot, false, input, output)?;
    }
    require_gate(fastboot, false, false)?;
    Ok(fastboot.getvar("unlocked")? == "yes")
}

fn perform(
    output: &mut impl Write,
    fastboot: &mut NativeFastboot,
    step: &mut usize,
    label: &str,
    arguments: &[&str],
) -> Result<(), CommandError> {
    writeln!(output, "[{}/22] {label}", *step).map_err(io_error)?;
    fastboot.command(arguments)?;
    *step += 1;
    Ok(())
}

fn vbmeta_arguments<'a>(partition: &'a str, image: &'a str) -> [&'a str; 5] {
    [
        "--disable-verity",
        "--disable-verification",
        "flash",
        partition,
        image,
    ]
}

fn missing_system_ext(output: &str) -> bool {
    output.contains("Could not open partition")
}

fn system_ext_size(output: &str) -> Option<u64> {
    let value = output
        .lines()
        .find_map(|line| line.trim().strip_prefix("partition-size:system_ext_a: "))?;
    u64::from_str_radix(value.trim_start_matches("0x"), 16).ok()
}

fn wait_for_mode(
    fastboot: &mut NativeFastboot,
    userspace: bool,
    input: &mut impl BufRead,
    output: &mut impl Write,
) -> Result<(), CommandError> {
    loop {
        match fastboot.wait_for_mode(userspace) {
            Ok(()) => return Ok(()),
            Err(error) if error.code() == "JR-CLI-USB-PERMISSION" => {
                writeln!(output, "\n{}", error).map_err(io_error)?;
                writeln!(
                    output,
                    "The R1 is still waiting safely. Do not unplug during an active transfer."
                )
                .map_err(io_error)?;
                write!(output, "Fix the USB permission, then press Enter to retry this same mode check, or type q to stop: ").map_err(io_error)?;
                output.flush().map_err(io_error)?;
                let mut answer = String::new();
                input.read_line(&mut answer).map_err(io_error)?;
                if answer.trim().eq_ignore_ascii_case("q") {
                    return Err(CommandError::new(
                        "JR-CLI-CANCELLED",
                        "stopped while the R1 remained in fastboot mode",
                    ));
                }
                if !answer.trim().is_empty() {
                    prompt::incorrect_then_retry_or_cancel(
                        input,
                        output,
                        "stopped while the R1 remained in fastboot mode",
                    )?;
                }
            }
            Err(error) => return Err(error),
        }
    }
}

fn require_gate(
    fastboot: &mut NativeFastboot,
    userspace: bool,
    require_unlocked: bool,
) -> Result<(), CommandError> {
    if fastboot.getvar("product")? != "k65v1_64_bsp" {
        return Err(CommandError::new(
            "JR-CLI-PRODUCT",
            "connected device is not the reviewed R1 product",
        ));
    }
    if fastboot.getvar("current-slot")? != "a" {
        return Err(CommandError::new("JR-CLI-SLOT", "R1 must use slot a"));
    }
    if fastboot.getvar("is-userspace")? != if userspace { "yes" } else { "no" } {
        return Err(CommandError::new(
            "JR-CLI-MODE",
            "R1 is in the wrong fastboot mode",
        ));
    }
    if require_unlocked && fastboot.getvar("unlocked")? != "yes" {
        return Err(CommandError::new(
            "JR-CLI-LOCKED",
            "R1 bootloader is not unlocked",
        ));
    }
    Ok(())
}

fn confirm(
    input: &mut impl BufRead,
    output: &mut impl Write,
    warning: &str,
    phrase: &str,
) -> Result<(), CommandError> {
    writeln!(output, "{warning}").map_err(io_error)?;
    loop {
        write!(output, "Type {phrase} to continue: ").map_err(io_error)?;
        output.flush().map_err(io_error)?;
        let mut answer = String::new();
        input.read_line(&mut answer).map_err(io_error)?;
        if answer.trim() == phrase {
            return Ok(());
        }
        prompt::incorrect_then_retry_or_cancel(
            input,
            output,
            "cancelled before the next device mutation",
        )?;
    }
}

fn io_error(error: io::Error) -> CommandError {
    CommandError::new("JR-CLI-IO", error.to_string())
}

#[cfg(test)]
mod tests {
    use super::{confirm, missing_system_ext, system_ext_size, vbmeta_arguments, SYSTEM_EXT_SIZE};
    use std::io::Cursor;

    #[test]
    fn destructive_confirmation_retries_after_incorrect_entry() {
        assert!(confirm(
            &mut Cursor::new("INSTALL JACKRABBIT\n"),
            &mut Vec::new(),
            "warning",
            "INSTALL JACKRABBIT"
        )
        .is_ok());
        let mut output = Vec::new();
        assert!(confirm(
            &mut Cursor::new("INSTALL\n\nINSTALL JACKRABBIT\n"),
            &mut output,
            "warning",
            "INSTALL JACKRABBIT"
        )
        .is_ok());
        assert!(String::from_utf8(output)
            .unwrap()
            .contains("ENTRY INCORRECT. WOULD YOU LIKE TO CANCEL?"));
        let error = confirm(
            &mut Cursor::new("INSTALL\ny\n"),
            &mut Vec::new(),
            "warning",
            "INSTALL JACKRABBIT",
        )
        .unwrap_err();
        assert_eq!(error.code(), "JR-CLI-CANCELLED");
        assert_eq!(SYSTEM_EXT_SIZE, "559304704");
    }

    #[test]
    fn every_vbmeta_write_uses_the_physically_accepted_flags() {
        assert_eq!(
            vbmeta_arguments("vbmeta_a", "vbmeta.img"),
            [
                "--disable-verity",
                "--disable-verification",
                "flash",
                "vbmeta_a",
                "vbmeta.img"
            ]
        );
    }

    #[test]
    fn accepts_fastboot_missing_partition_message_even_with_zero_exit() {
        assert!(missing_system_ext(
            "getvar:partition-size:system_ext_a FAILED (remote: 'Could not open partition')"
        ));
        assert!(!missing_system_ext(
            "partition-size:system_ext_a: 0x21565000"
        ));
        assert_eq!(
            system_ext_size("partition-size:system_ext_a: 0x21565000"),
            Some(559_304_704)
        );
        assert_eq!(
            system_ext_size("partition-size:system_ext_a: 21565000"),
            Some(559_304_704)
        );
        assert_eq!(system_ext_size("Finished. Total time: 0.001s"), None);
    }
}
