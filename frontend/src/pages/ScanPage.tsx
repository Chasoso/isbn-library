import { BrowserMultiFormatReader } from "@zxing/browser";
import {
  BarcodeFormat,
  ChecksumException,
  DecodeHintType,
  FormatException,
  NotFoundException,
} from "@zxing/library";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppLayout } from "../app-shell";
import { normalizeIsbn } from "../lib/isbn";

export function ScanPage() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const controlsRef = useRef<{ stop: () => void } | null>(null);
  const [message, setMessage] = useState<string | null>("バーコードを中央に合わせてください。");
  const [isbnInput, setIsbnInput] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const [cameraUnavailable, setCameraUnavailable] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);

  useEffect(() => {
    const hints = new Map();
    hints.set(DecodeHintType.POSSIBLE_FORMATS, [
      BarcodeFormat.EAN_13,
      BarcodeFormat.EAN_8,
      BarcodeFormat.UPC_A,
      BarcodeFormat.UPC_E,
    ]);
    hints.set(DecodeHintType.TRY_HARDER, true);

    const reader = new BrowserMultiFormatReader(hints, {
      delayBetweenScanAttempts: 20,
      delayBetweenScanSuccess: 500,
    });

    let active = true;
    let detected = false;

    const onDetected = async (text: string): Promise<void> => {
      if (detected) return;

      const isbn = normalizeIsbn(text);
      if (!isbn) {
        setMessage("ISBNとして読み取れませんでした。");
        return;
      }

      detected = true;
      controlsRef.current?.stop();
      setMessage(`ISBN ${isbn} を読み取りました。`);
      if (active) {
        navigate(`/result/${isbn}`);
      }
    };

    const start = async (): Promise<void> => {
      setCameraReady(false);
      setCameraUnavailable(false);
      setMessage("バーコードを中央に合わせてください。");

      if (!videoRef.current) {
        setCameraUnavailable(true);
        setMessage("この環境ではカメラを利用できません。");
        return;
      }

      try {
        const devices = await BrowserMultiFormatReader.listVideoInputDevices();
        const preferredDevice =
          devices.find((device) => /back|rear|environment|背面/i.test(device.label)) ?? devices[0];

        if (!preferredDevice) {
          setCameraUnavailable(true);
          setMessage("この環境ではカメラを利用できません。");
          return;
        }

        const controls = await reader.decodeFromConstraints(
          {
            audio: false,
            video: {
              deviceId: { exact: preferredDevice.deviceId },
              facingMode: "environment",
              width: { ideal: 1280 },
              height: { ideal: 720 },
            },
          },
          videoRef.current,
          (result, error) => {
            if (result) {
              void onDetected(result.getText());
              return;
            }

            if (
              error &&
              !(
                error instanceof NotFoundException ||
                error instanceof ChecksumException ||
                error instanceof FormatException
              )
            ) {
              setMessage("読み取り中にエラーが発生しました。");
            }
          },
        );

        controlsRef.current = controls;
        setCameraUnavailable(false);
        setCameraReady(true);
      } catch (error) {
        const detail = error instanceof Error ? error.message : String(error);
        if (/Permission|denied|NotAllowed/i.test(detail)) {
          setCameraUnavailable(true);
          setMessage("カメラの使用が許可されていません。");
          return;
        }
        if (/secure|https|origin/i.test(detail)) {
          setCameraUnavailable(true);
          setMessage("カメラは HTTPS または localhost でのみ利用できます。");
          return;
        }
        setCameraUnavailable(true);
        setMessage("この環境ではカメラを利用できません。");
      }
    };

    void start();

    return () => {
      active = false;
      controlsRef.current?.stop();
      controlsRef.current = null;
    };
  }, [navigate, retryCount]);

  const submitManualIsbn = (): void => {
    const isbn = normalizeIsbn(isbnInput);
    if (!isbn) {
      setMessage("ISBNの形式を確認してください。");
      return;
    }

    navigate(`/result/${isbn}`);
  };

  return (
    <AppLayout title="スキャン">
      <section className="panel scan-panel">
        {cameraUnavailable ? (
          <div className="scan-manual scan-manual-first">
            <label>
              ISBN
              <input
                value={isbnInput}
                onChange={(event) => setIsbnInput(event.target.value)}
                placeholder="9784860648114"
                inputMode="numeric"
                aria-label="ISBN"
              />
            </label>
            <div className="scan-manual-actions">
              <button type="button" className="primary-button" onClick={submitManualIsbn}>
                検索
              </button>
              <button
                type="button"
                className="ghost-button scan-retry-button"
                onClick={() => setRetryCount((count) => count + 1)}
              >
                カメラを再試行
              </button>
            </div>
          </div>
        ) : null}

        {!cameraUnavailable && cameraReady ? (
          <div className="scanner-shell">
            <video ref={videoRef} className="scanner-video" muted playsInline autoPlay />
            <div className="scanner-overlay" aria-hidden="true">
              <div className="scanner-target" />
            </div>
          </div>
        ) : null}

        {!cameraUnavailable ? (
          <div className="scan-manual">
            <label>
              ISBN
              <input
                value={isbnInput}
                onChange={(event) => setIsbnInput(event.target.value)}
                placeholder="9784860648114"
                inputMode="numeric"
                aria-label="ISBN"
              />
            </label>
            <div className="scan-manual-actions">
              <button type="button" className="primary-button" onClick={submitManualIsbn}>
                検索
              </button>
              <button
                type="button"
                className="ghost-button scan-retry-button"
                onClick={() => setRetryCount((count) => count + 1)}
              >
                カメラを再試行
              </button>
            </div>
          </div>
        ) : null}

        {message ? <p className="subtle scan-message">{message}</p> : null}
      </section>
    </AppLayout>
  );
}
