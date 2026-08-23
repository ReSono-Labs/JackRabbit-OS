mod command;
mod diagnose;
mod fastboot;
mod install;
mod physical;
mod preloader;
mod prompt;
mod release;

use command::Command;

fn main() {
    let result = Command::from_args(std::env::args().skip(1)).and_then(Command::run);
    if let Err(error) = result {
        eprintln!("{}: {}", error.code(), error);
        std::process::exit(2);
    }
}

#[cfg(test)]
mod tests {
    use super::command::Command;

    #[test]
    fn arbitrary_mutating_and_unimplemented_commands_do_not_exist() {
        for name in [
            "resume", "repair", "restore", "flash", "fastboot", "erase", "reboot",
        ] {
            assert!(Command::from_args([name.to_string()].into_iter()).is_err());
        }
        assert!(
            Command::from_args(["install".to_string(), "release".to_string()].into_iter()).is_ok()
        );
    }
}
