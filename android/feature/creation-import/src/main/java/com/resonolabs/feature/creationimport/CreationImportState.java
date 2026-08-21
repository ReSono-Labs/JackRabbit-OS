package com.resonolabs.feature.creationimport;

/** Explicit states for the removable on-device Creation import flow. */
public enum CreationImportState {
    POSITIONING, LIVE, DECODING, PREFLIGHT, REVIEW, INSTALLING, SUCCESS, ERROR
}
