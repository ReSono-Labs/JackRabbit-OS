use crate::command::CommandError;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};

pub const RELEASE_ID: &str = "jackrabbit-stock-r1-current-v0.2";

pub struct Artifact {
    pub path: &'static str,
    pub size: u64,
    pub sha256: &'static str,
}

pub const ARTIFACTS: [Artifact; 12] = [
    Artifact {
        path: "images/stock/boot.img",
        size: 33_554_432,
        sha256: "0480ffab24e208ca20e761ebc07c15c0992ee3c91a3f55377731fdec532ae30f",
    },
    Artifact {
        path: "images/stock/super.img",
        size: 2_110_680_916,
        sha256: "d723922e8b0308c1c2363da513592a44cb20c21ed4023e55f05f3a0b8578b7a2",
    },
    Artifact {
        path: "images/stock/vbmeta.img",
        size: 4_096,
        sha256: "a4b69a84ae568d6340fc97b1cb6a564126d4edd25721e998cb148982b0a52089",
    },
    Artifact {
        path: "images/stock/vbmeta_system.img",
        size: 4_096,
        sha256: "10d7c932c1b2974efcb35288e2ceea9d35aff2480a19a4882d86f0e2a245d373",
    },
    Artifact {
        path: "images/stock/vbmeta_vendor.img",
        size: 4_096,
        sha256: "5b23d1e31f4b8b196b988ae1490a95fba649f8403dd2b11309efa612ac41ddfc",
    },
    Artifact {
        path: "images/jackrabbit/system.img",
        size: 1_400_053_760,
        sha256: "c7a7078dd55bded36ff3e2cf5a90367bbfcf9fd698aaf9646ddbf417748bb8c8",
    },
    Artifact {
        path: "images/jackrabbit/product.img",
        size: 407_642_112,
        sha256: "eac03525513be044b804c0a33711eda75922d0fc25ef815ad4f2efa6168e1c41",
    },
    Artifact {
        path: "images/cipheros/system_ext.img",
        size: 559_304_704,
        sha256: "db08515c52d0e679d1926bdc11719935efd3bac581e683e07a15bfe49f4f1dd9",
    },
    Artifact {
        path: "images/cipheros/vendor.img",
        size: 369_319_936,
        sha256: "d0448bd943db89fa795154f99ee91648e355853d594fb822f6f1ed5dd101dfcd",
    },
    Artifact {
        path: "images/cipheros/vbmeta.img",
        size: 4_096,
        sha256: "36fedb0f1d79bbf9bebe509320296346667ced09c1f46c0bfb8719b52c18c1f2",
    },
    Artifact {
        path: "images/cipheros/vbmeta_system.img",
        size: 4_096,
        sha256: "89333175d7f1fa9c368c87e39015213726f2e4f469198f9c8a44a2ceafb4245e",
    },
    Artifact {
        path: "images/cipheros/vbmeta_vendor.img",
        size: 4_096,
        sha256: "4bf39aadc797948e0cceb1332220f7822d5801b21edae9ad44bd16692afa1158",
    },
];

pub fn verify(root: &Path, mut progress: impl FnMut(usize, &Artifact)) -> Result<(), CommandError> {
    for (index, artifact) in ARTIFACTS.iter().enumerate() {
        progress(index, artifact);
        let path = root.join(artifact.path);
        let metadata = path.metadata().map_err(|_| {
            CommandError::new(
                "JR-CLI-RELEASE-MISSING",
                format!("missing release file: {}", artifact.path),
            )
        })?;
        if metadata.len() != artifact.size {
            return Err(CommandError::new(
                "JR-CLI-RELEASE-SIZE",
                format!("wrong file size: {}", artifact.path),
            ));
        }
        let mut file = File::open(&path)
            .map_err(|error| CommandError::new("JR-CLI-RELEASE-READ", error.to_string()))?;
        let mut digest = Sha256::new();
        let mut buffer = [0_u8; 1024 * 1024];
        loop {
            let read = file
                .read(&mut buffer)
                .map_err(|error| CommandError::new("JR-CLI-RELEASE-READ", error.to_string()))?;
            if read == 0 {
                break;
            }
            digest.update(&buffer[..read]);
        }
        if format!("{:x}", digest.finalize()) != artifact.sha256 {
            return Err(CommandError::new(
                "JR-CLI-RELEASE-HASH",
                format!("changed release file: {}", artifact.path),
            ));
        }
    }
    Ok(())
}

pub fn path(root: &Path, relative: &str) -> PathBuf {
    root.join(relative)
}

#[cfg(test)]
mod tests {
    use super::{verify, ARTIFACTS, RELEASE_ID};
    use std::path::Path;

    #[test]
    fn release_inventory_is_the_exact_current_twelve_file_set() {
        assert_eq!(RELEASE_ID, "jackrabbit-stock-r1-current-v0.2");
        assert_eq!(ARTIFACTS.len(), 12);
        assert_eq!(ARTIFACTS[5].path, "images/jackrabbit/system.img");
        assert_eq!(
            ARTIFACTS[5].sha256,
            "c7a7078dd55bded36ff3e2cf5a90367bbfcf9fd698aaf9646ddbf417748bb8c8"
        );
        assert_eq!(
            ARTIFACTS[2].sha256,
            "a4b69a84ae568d6340fc97b1cb6a564126d4edd25721e998cb148982b0a52089"
        );
    }

    #[test]
    fn missing_release_fails_before_device_access() {
        assert_eq!(
            verify(Path::new("definitely-absent"), |_, _| {})
                .unwrap_err()
                .code(),
            "JR-CLI-RELEASE-MISSING"
        );
    }
}
