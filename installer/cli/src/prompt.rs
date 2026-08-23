use crate::command::CommandError;
use std::io::{BufRead, Write};

pub fn incorrect_then_retry_or_cancel(
    input: &mut impl BufRead,
    output: &mut impl Write,
    cancel_message: &str,
) -> Result<(), CommandError> {
    writeln!(output, "\nENTRY INCORRECT. WOULD YOU LIKE TO CANCEL?").map_err(io_error)?;
    loop {
        write!(
            output,
            "Type Y to cancel, or press Enter to return to the same prompt: "
        )
        .map_err(io_error)?;
        output.flush().map_err(io_error)?;
        let mut answer = String::new();
        input.read_line(&mut answer).map_err(io_error)?;
        match answer.trim().to_ascii_lowercase().as_str() {
            "y" | "yes" => return Err(CommandError::new("JR-CLI-CANCELLED", cancel_message)),
            "" | "n" | "no" => return Ok(()),
            _ => writeln!(output, "Please type Y to cancel, or press Enter to retry.")
                .map_err(io_error)?,
        }
    }
}

fn io_error(error: std::io::Error) -> CommandError {
    CommandError::new("JR-CLI-IO", error.to_string())
}

#[cfg(test)]
mod tests {
    use super::incorrect_then_retry_or_cancel;
    use std::io::Cursor;

    #[test]
    fn empty_answer_returns_to_the_same_prompt() {
        let mut output = Vec::new();
        incorrect_then_retry_or_cancel(&mut Cursor::new("\n"), &mut output, "cancelled").unwrap();
        assert!(String::from_utf8(output)
            .unwrap()
            .contains("ENTRY INCORRECT. WOULD YOU LIKE TO CANCEL?"));
    }

    #[test]
    fn explicit_yes_cancels() {
        let error =
            incorrect_then_retry_or_cancel(&mut Cursor::new("yes\n"), &mut Vec::new(), "cancelled")
                .unwrap_err();
        assert_eq!(error.code(), "JR-CLI-CANCELLED");
    }
}
