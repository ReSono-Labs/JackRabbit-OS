import { ContractError } from "../release/contract-validator.mjs";

export const R1_PRELOADER_USB = Object.freeze({ usbVendorId: 0x0e8d, usbProductId: 0x2000 });
const fastbootPayload = new TextEncoder().encode("FASTBOOT");

function fail(code, message) {
  throw new ContractError(code, message);
}

export async function requestR1Preloader(serial = navigator.serial) {
  if (!serial?.requestPort) fail("JR-CAPABILITY-WEBSERIAL", "Web Serial is unavailable");
  return serial.requestPort({ filters: [R1_PRELOADER_USB] });
}

export async function sendFastbootEntry(port) {
  let writer;
  let opened = false;
  try {
    await port.open({ baudRate: 115200 });
    opened = true;
    if (!port.writable) fail("JR-PRELOADER-WRITABLE", "selected preloader port is not writable");
    writer = port.writable.getWriter();
    await writer.write(fastbootPayload);
    return Object.freeze({ payloadBytes: fastbootPayload.byteLength, transferComplete: true, deviceModeUnverified: true });
  } catch (error) {
    if (error instanceof ContractError) throw error;
    throw new ContractError("JR-PRELOADER-TRANSFER", "FASTBOOT entry transfer failed");
  } finally {
    if (writer) writer.releaseLock();
    if (opened) await port.close();
  }
}
