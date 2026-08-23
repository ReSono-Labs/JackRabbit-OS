# Using JackRabbit

This guide begins with a JackRabbit R1 that is already running. It covers the device UI and the management console that the R1 serves to a browser on the same local network.

JackRabbit is under active development. When a capability has incomplete physical acceptance, the guide says so directly.

## Device controls

JackRabbit is the R1 HOME surface. Voice is the first page and Cards is the second.

- Use the touch screen for buttons, tabs, lists, and sliders.
- Use the scroll wheel for supported list navigation.
- Use the side button for the context-sensitive action exposed by the current page.
- Use the power button normally. JackRabbit keeps the screen awake while its activity is visible.

Open the gear icon at the upper right for Settings. The running-person icon at the top opens the native Background Agent run surface.

## Connect Wi-Fi and open Management

1. On the R1, open **Settings → Wi-Fi**.
2. Select the network and enter its credentials when prompted.
3. Confirm that the R1 and the browser device are on the same local network.
4. Open **Settings → Management**.
5. Note the HTTPS address displayed by the R1.
6. Read the displayed pairing code. It is a one-time six-digit code and expires after five minutes; use **Refresh** if a new code is needed.
7. Enter the displayed address in the browser.
8. Follow the browser or operating system's certificate-trust flow. The management page provides the R1's local certificate for download when needed.
9. Enter the pairing code in the browser.

A paired browser session lasts 30 minutes. If authorization expires, use **Refresh** on the R1 and pair again with the newly displayed code.

The address is local to the active Wi-Fi or Ethernet network. A cellular address is not advertised as the management address.

## Connect OpenAI access

Open **AI & Voice** in the management console.

### ChatGPT/Codex subscription access

1. Choose the ChatGPT/Codex connection action.
2. Follow the device-code authorization instructions shown by the management page.
3. Complete authorization in the OpenAI page opened by your browser.
4. Return to JackRabbit and wait for the connection state to report connected.

The authorization attempt is time-limited. JackRabbit exchanges and refreshes the resulting subscription credentials through its trusted runtime boundary. Disconnecting removes the saved authorization.

### OpenAI Platform access

1. Enter an owner-supplied OpenAI Platform API key in the Platform field.
2. Save the setting.
3. Wait for the runtime to refresh the model list reported by the provider.

The API key is sealed by the Android credential owner and is not stored as plaintext in the Python database.

### Choose models and reasoning

After connecting an access method:

1. Select the access path JackRabbit should use.
2. Select a text model.
3. Select a Realtime model.
4. Select the reasoning effort.
5. Save the settings and confirm the page reflects the selection.

Subscription choices come from JackRabbit's current catalog. Platform choices are filtered from the account's reported model list. Availability in either selector is not a guarantee that the model has completed physical R1 acceptance.

## Start and stop Voice

1. Return to the native **Voice** page.
2. Press the central microphone control.
3. Watch the state label:
   - `connecting` means the WebRTC session is being established.
   - `live` means the session can receive speech.
   - `responding` means the assistant is producing its response.
   - `error` means the session did not continue; the page should display a truthful failure state.
4. Speak normally while the session is live.
5. Press the active Voice control to end the session.

The native Android path owns microphone and speaker media. Python and MCP carry agent state and tool calls, not the high-rate audio stream.

If Voice cannot connect, verify the selected access method, model availability, network connectivity, and provider authorization in **AI & Voice**.

## Use Cards

Open the **Cards** tab from the native navigation. The deck contains:

- Calendar, which opens the upcoming-event view.
- Tasks, which opens local tasks.
- Any enabled static Creations.

Select a Card to open it. Use the page's back behavior to return to the deck, and choose Voice to return to the first page.

## Connect Calendar

Open **Connections → Calendar** in Management.

1. Add a connection and choose the available type appropriate to the source: ICS file, ICS subscription, or CalDAV.
2. Enter the label, endpoint or source details, and credentials requested by the form.
3. Save and wait for the connection status to report the synchronization result.
4. Open **Cards → Calendar** on the R1 to view upcoming events.

JackRabbit accepts up to two Calendar accounts and schedules synchronization every five minutes. The source's discovered capabilities determine whether create, update, or delete tools are available. Read-only sources reject mutations.

The supplied R1 screenshot proves a real upcoming event can reach the native Calendar view. Not every Calendar provider and mutation path has completed physical acceptance.

## Connect Mail

Open **Connections → Mail** in Management.

1. Add an account.
2. Enter the IMAP and SMTP details requested by the form.
3. Save the account and wait for validation and synchronization status.

JackRabbit accepts up to three Mail accounts and schedules synchronization every five minutes. It can read locally synchronized messages, change read/unread state, prepare drafts, and send through SMTP. A sent message is also appended to the provider's Sent folder when supported.

Sending requires explicit confirmation. The approval is single-use and is bound to the exact draft content and the approving user utterance. Changing the draft invalidates the earlier approval. No model-facing Mail delete, trash, expunge, or purge operation exists.

The management API returns account configuration and status, not message content. Provider-specific physical acceptance is still partial.

## Use Tasks

Open **Cards → Tasks** to view local tasks. Voice can create, list, update, complete, and remove task records through the shared tool boundary.

Tasks currently store a title and completion state. They do not provide due dates, schedules, reminders, or notifications.

## Manage the Library

Open **Library** in Management. Its tabs separate Skills, Plugins, MCP, Tools, and Creations.

### Skills

Skills are `SKILL.md` instruction documents assigned to Voice or Background Agent. Import the appropriate document, review its destination, and confirm replacement when that agent already has a document.

### Plugins

Plugin packages declare their identity and components in `plugin.json` and can include Skills, MCP connections, and Cards. JackRabbit preflights imports before confirmation, records component ownership, and supports enable, disable, replacement, and removal.

Known limitation: replacing a Plugin that previously supplied a Card with one that supplies no Card can leave the old Card registered in a disabled state.

### MCP and Tools

MCP connections define external model-facing tool sources. After adding a connection, run discovery, inspect the tools, and enable only the connection and audiences you intend to expose. Effective access is the intersection of the declared permission and the selected Voice or Background Agent audience.

The Tools tab shows built-in and discovered tools and their current audience.

### Creations

Creations are bounded static ZIP packages containing an `index.html`. After a Creation passes inspection and is enabled, it appears in the native Cards deck and renders inside a confined WebView.

The native Settings page also exposes Creation import. QR descriptors can identify Creation sources; linked sources must use public HTTPS URLs. Imports reject unsafe paths, symbolic links, encrypted entries, and archives outside the configured size and compression limits.

## Use Background Agent

Background Agent is implemented development functionality whose latest corrections still need a recorded successful physical delegated run.

### Configure it

1. Open **Background Agent** in Management.
2. Enable or disable execution.
3. Choose the available model, reasoning effort, tools, and bounded run limits.
4. Save the settings.

The defaults are 300 seconds, 24 model turns, 40 tool calls, two review rounds, and an 8 MiB workspace.

### Start or inspect a run

Voice can delegate a goal through the Background Agent goal tool. On the R1, use the running-person icon to open the native run surface. In Management, use **Run Logs** for lifecycle and delivery status and **Reasoning Logs** for provider-returned summaries and bounded tool metadata.

Possible states include queued, running, reviewing, repairing, completed, failed, and cancelled. A failure is retained as a failure rather than being presented as completed work. Terminal runs can be removed from Management.

Reasoning Logs do not contain hidden chain-of-thought, tool arguments, or tool results.

## Native Settings reference

- **Wi-Fi:** Scan and connect to wireless networks.
- **Bluetooth:** Change the Bluetooth enabled state.
- **Management:** View the local address and pairing code, and refresh management status.
- **AI:** View or change provider access, models, and reasoning; enter a Platform key.
- **Creations:** Open native Creation import.
- **Sound:** Adjust the device media volume.
- **Display:** Adjust screen brightness. The wheel navigates; use touch to change the slider.
- **About:** View runtime information and request a runtime restart.

## Troubleshooting

### The management page does not open

- Confirm the browser and R1 are on the same local network.
- Reopen **Settings → Management** and use the currently displayed HTTPS address.
- Confirm the browser trusts the certificate presented by this R1.
- Do not substitute a cellular address; JackRabbit advertises the active local Wi-Fi or Ethernet address.

### Pairing fails or expires

- Use **Refresh** on the R1 to display a new code. Codes are one-time and expire after five minutes.
- Enter the new code in the same HTTPS origin shown by the device.
- If a previously paired page has been idle, pair again; browser sessions expire after 30 minutes.

### Voice remains in `connecting` or enters `error`

- Check network connectivity.
- In **AI & Voice**, confirm the selected access method is connected and the selected Realtime model is still available.
- Reauthorize ChatGPT/Codex if its connection has expired, or resave a valid Platform key.
- Open **Settings → About** and restart the runtime if its status is not ready.

### Calendar or Mail does not refresh

- Open **Connections** and inspect the account's last synchronization state and detail.
- Verify the endpoint, credentials, TLS mode, and provider availability.
- Allow for the five-minute synchronization cadence.
- For Calendar mutations, confirm the source reports the required capability.

### An extension is unavailable

- Confirm that the package passed preflight and confirmation.
- Confirm the Skill, Plugin, MCP connection, or Creation is enabled.
- For MCP tools, confirm discovery succeeded and the intended agent audience is allowed.
- Review import recovery or quarantine state if an earlier lifecycle action was interrupted.

## Privacy reminders

- Voice and agent requests send the data needed for the request to the selected OpenAI access path.
- Connected Mail and Calendar sources exchange data with their configured servers.
- Web search and outbound MCP tools send relevant request data to those services.
- Treat imported packages and external MCP servers as third-party components and review their declared access before enabling them.
- Management is local-network scoped, but it still exposes owner controls; pair only browsers you trust.

Return to the [JackRabbit README](README.md).
