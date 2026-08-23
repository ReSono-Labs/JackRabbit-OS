use crate::command::CommandError;
use crate::prompt;
use serde::Deserialize;
use std::io::{BufRead, IsTerminal, Write};

const PROMPT_CONTRACT: &str = include_str!("../../contracts/preparation-prompts-v1.json");
const OFFICIAL_ENTRY_URL: &str = "https://rabbit-hmi-oss.github.io/flashing/";

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct PromptContract {
    schema_version: u8,
    prompts: Vec<Prompt>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Prompt {
    id: String,
    phase: String,
    category: String,
    title: String,
    #[serde(rename = "reason")]
    _reason: String,
    action: String,
    expected: String,
    warning: String,
    verification: String,
    cancel: String,
    next_states: Vec<String>,
    surfaces: Vec<String>,
    href: Option<String>,
    link_label: Option<String>,
}

pub fn run(
    input: &mut impl BufRead,
    output: &mut impl Write,
    detected_unlocked: Option<bool>,
) -> Result<(), CommandError> {
    let contract = load_contract()?;
    let steps: Vec<_> = contract
        .prompts
        .iter()
        .filter(|prompt| prompt.surfaces.iter().any(|surface| surface == "cli"))
        .filter(|prompt| match detected_unlocked {
            None => true,
            Some(false) => matches!(prompt.id.as_str(), "prepare-account" | "back-up"),
            Some(true) => prompt.id == "back-up",
        })
        .collect();

    let clear_between_steps = std::io::stdout().is_terminal();
    for (index, step) in steps.iter().enumerate() {
        if clear_between_steps {
            write!(output, "\x1b[2J\x1b[H").map_err(io_error)?;
        }
        writeln!(
            output,
            "JackRabbit R1 setup                                      Step {} of {}\n{}\n\n{}\n\nDO THIS\n{}\n\nEXPECTED\n{}\n\nWARNING\n{}",
            index + 1,
            steps.len(),
            detected_status(detected_unlocked),
            step.title,
            step.action,
            step.expected,
            step.warning
        )
        .map_err(io_error)?;
        if let (Some(label), Some(href)) = (&step.link_label, &step.href) {
            writeln!(output, "{label}: {href}").map_err(io_error)?;
        }
        loop {
            write!(
                output,
                "\n------------------------------------------------------------\nPress Enter after this is complete, or type q to stop: "
            )
            .map_err(io_error)?;
            output.flush().map_err(io_error)?;
            let mut answer = String::new();
            input.read_line(&mut answer).map_err(io_error)?;
            if answer.trim().eq_ignore_ascii_case("q") {
                return Err(CommandError::new("JR-CLI-CANCELLED", &step.cancel));
            }
            if answer.trim().is_empty() {
                break;
            }
            prompt::incorrect_then_retry_or_cancel(input, output, &step.cancel)?;
        }
        writeln!(output).map_err(io_error)?;
    }
    if clear_between_steps {
        write!(output, "\x1b[2J\x1b[H").map_err(io_error)?;
    }
    match detected_unlocked {
        Some(_) => writeln!(output, "Preparation complete. Keep the detected R1 connected in bootloader FASTBOOT. Nothing will be written until the final installation confirmation.").map_err(io_error),
        None => writeln!(output, "Preparation complete. The installer will now wait for the powered-off R1 and place it in bootloader FASTBOOT. Nothing will be written until the final installation confirmation.").map_err(io_error),
    }
}

fn detected_status(detected_unlocked: Option<bool>) -> &'static str {
    match detected_unlocked {
        Some(true) => "\nR1 STATUS: Bootloader FASTBOOT detected and unlocked. Leave it connected.",
        Some(false) => "\nR1 STATUS: Bootloader FASTBOOT detected and locked. Leave it connected.",
        None => "",
    }
}

fn load_contract() -> Result<PromptContract, CommandError> {
    let contract: PromptContract = serde_json::from_str(PROMPT_CONTRACT).map_err(|_| {
        CommandError::new(
            "JR-CLI-PROMPT-CONTRACT",
            "the embedded physical prompt contract is invalid",
        )
    })?;
    if contract.schema_version != 1 || contract.prompts.is_empty() {
        return Err(CommandError::new(
            "JR-CLI-PROMPT-CONTRACT",
            "the embedded physical prompt contract version is unsupported",
        ));
    }
    for prompt in &contract.prompts {
        if prompt.id.is_empty()
            || prompt.phase.is_empty()
            || prompt.category.is_empty()
            || prompt.verification.is_empty()
            || prompt.next_states.is_empty()
            || prompt.surfaces.is_empty()
            || prompt.href.is_some() != prompt.link_label.is_some()
        {
            return Err(CommandError::new(
                "JR-CLI-PROMPT-CONTRACT",
                "the embedded physical prompt contract is incomplete",
            ));
        }
        if prompt.id == "open-official-entry" && prompt.href.as_deref() != Some(OFFICIAL_ENTRY_URL)
        {
            return Err(CommandError::new(
                "JR-CLI-PROMPT-CONTRACT",
                "the official FASTBOOT entry URL is not the reviewed source",
            ));
        }
    }
    Ok(contract)
}

fn io_error(error: std::io::Error) -> CommandError {
    CommandError::new("JR-CLI-IO", error.to_string())
}

#[cfg(test)]
mod tests {
    use super::{load_contract, run};
    use std::io::Cursor;

    #[test]
    fn prompts_every_physical_step_in_contract_order() {
        let mut output = Vec::new();
        run(&mut Cursor::new("\n\n\n\n"), &mut output, None).unwrap();
        let text = String::from_utf8(output).unwrap();
        let positions: Vec<_> = [
            "Request developer mode",
            "Back up the R1",
            "Prepare the hardware",
            "Let JackRabbit enter FASTBOOT",
        ]
        .iter()
        .map(|value| text.find(value).unwrap())
        .collect();
        assert!(positions.windows(2).all(|pair| pair[0] < pair[1]));
        assert!(text.contains("sends only FASTBOOT at 115200 baud"));
    }

    #[test]
    fn embedded_contract_has_stable_typed_steps() {
        let contract = load_contract().unwrap();
        assert_eq!(contract.schema_version, 1);
        assert!(contract
            .prompts
            .iter()
            .all(|prompt| !prompt.next_states.is_empty()));
    }

    #[test]
    fn cancellation_is_fail_safe() {
        let error = run(&mut Cursor::new("q\n"), &mut Vec::new(), None).unwrap_err();
        assert_eq!(error.code(), "JR-CLI-CANCELLED");
    }

    #[test]
    fn incorrect_entry_returns_to_the_same_step() {
        let mut output = Vec::new();
        let error = run(&mut Cursor::new("done\n\nq\n"), &mut output, None).unwrap_err();
        assert_eq!(error.code(), "JR-CLI-CANCELLED");
        assert!(String::from_utf8(output)
            .unwrap()
            .contains("ENTRY INCORRECT. WOULD YOU LIKE TO CANCEL?"));
    }

    #[test]
    fn detected_fastboot_skips_power_cycle_and_entry_prompts() {
        let mut output = Vec::new();
        run(&mut Cursor::new("\n"), &mut output, Some(true)).unwrap();
        let text = String::from_utf8(output).unwrap();
        assert!(text.contains("Bootloader FASTBOOT detected and unlocked"));
        assert!(text.contains("Back up the R1"));
        assert!(!text.contains("Prepare the hardware"));
        assert!(!text.contains("Let JackRabbit enter FASTBOOT"));
    }
}
