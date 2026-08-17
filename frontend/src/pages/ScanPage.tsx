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

function useCompactLayout(): boolean {
  const [compact, setCompact] = useState(() =>
    typeof window !== "undefined" ? window.matchMedia("(max-width: 480px)").matches : false,
  );

  useEffect(() => {
    const media = window.matchMedia("(max-width: 480px)");
    const update = () => setCompact(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  return compact;
}

export function ScanPage() {
  const navigate = useNavigate();
  const compact = useCompactLayout();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const controlsRef = useRef<{ stop: () => void } | null>(null);
  const [message, setMessage] = useState("カメラで ISBN を読み取るか、手入力してください。");
  const [isbnInput, setIsbnInput] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const [cameraUnavailable, setCameraUnavailable] = useState(false);

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
        setMessage("ISBN として読み取れませんでした。もう一度かざしてください。");
        return;
      }

      detected = true;
      controlsRef.current?.stop();
      setMessage(`ISBN ${isbn} を読み取りました。結果画面へ移動します。`);
      if (active) {
        navigate(`/result/${isbn}`);
      }
    };

    const start = async (): Promise<void> => {
      if (!videoRef.current) {
        setCameraUnavailable(true);
        setMessage("この環境ではカメラを利用できません。ISBNを手入力してください。");
        return;
      }

      try {
        const devices = await BrowserMultiFormatReader.listVideoInputDevices();
        const preferredDevice =
          devices.find((device) => /back|rear|environment|背面/i.test(device.label)) ?? devices[0];

        if (!preferredDevice) {
          setCameraUnavailable(true);
          setMessage("この環境ではカメラを利用できません。ISBNを手入力してください。");
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
              setMessage("読み取り中にエラーが発生しました。少し位置を変えてください。");
            }
          },
        );

        controlsRef.current = controls;
        setCameraUnavailable(false);
        setMessage("バーコードを中央の枠に合わせてください。");
      } catch (error) {
        const detail = error instanceof Error ? error.message : String(error);
        if (/Permission|denied|NotAllowed/i.test(detail)) {
          setCameraUnavailable(true);
          setMessage("カメラの使用が許可されていません。ブラウザ設定を確認してください。");
          return;
        }
        if (/secure|https|origin/i.test(detail)) {
          setCameraUnavailable(true);
          setMessage("カメラは HTTPS または localhost でのみ利用できます。");
          return;
        }
        setCameraUnavailable(true);
        setMessage("この環境ではカメラを利用できません。ISBNを手入力してください。");
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
      setMessage("ISBN の形式を確認してください。");
      return;
    }

    navigate(`/result/${isbn}`);
  };

  return (
    <AppLayout title="スキャン" subtitle="ISBN を読み取って、蔵書登録へ進みます。">
      <section className="panel scan-panel">
        <div className="section-heading">
          <div>
            <p className="section-label">ISBN スキャン</p>
            <h3>ISBN を読み取る</h3>
          </div>
        </div>

        {(cameraUnavailable || compact) ? (
          <div className="scan-manual scan-manual-first">
            <label>
              ISBNを入力
              <input
                value={isbnInput}
                onChange={(event) => setIsbnInput(event.target.value)}
                placeholder="9784860648114"
                inputMode="numeric"
                aria-label="ISBNを入力"
              />
            </label>
            <div className="scan-manual-actions">
              <button type="button" className="primary-button" onClick={submitManualIsbn}>
                確認して検索
              </button>
              <button type="button" className="ghost-button" onClick={() => setRetryCount((count) => count + 1)}>
                カメラを再試行
              </button>
            </div>
          </div>
        ) : null}

        {!cameraUnavailable ? (
          <div className="scanner-shell">
            <video ref={videoRef} className="scanner-video" muted playsInline autoPlay />
            <div className="scanner-overlay" aria-hidden="true">
              <div className="scanner-target" />
            </div>
          </div>
        ) : null}

        <p className="subtle scan-message">{message}</p>

        {!cameraUnavailable && !compact ? (
          <div className="scan-manual">
            <label>
              ISBNを入力
              <input
                value={isbnInput}
                onChange={(event) => setIsbnInput(event.target.value)}
                placeholder="9784860648114"
                inputMode="numeric"
                aria-label="ISBNを入力"
              />
            </label>
            <div className="scan-manual-actions">
              <button type="button" className="primary-button" onClick={submitManualIsbn}>
                確認して検索
              </button>
              <button type="button" className="ghost-button" onClick={() => setRetryCount((count) => count + 1)}>
                カメラを再試行
              </button>
            </div>
          </div>
        ) : null}

        <ul className="scan-tips">
          <li>バーコードをまっすぐ枠の中央へ合わせてください。</li>
          <li>うまく読めないときは、少し離して向きを変えてください。</li>
          <li>明るい場所で撮ると読み取りやすくなります。</li>
        </ul>
      </section>
    </AppLayout>
  );
}
