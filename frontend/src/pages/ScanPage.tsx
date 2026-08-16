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
  const [message, setMessage] = useState("裏表紙の ISBN バーコードを枠に合わせてください。");
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
        setMessage("ISBN として読み取れませんでした。少し離して、もう一度合わせてください。");
        return;
      }

      detected = true;
      controlsRef.current?.stop();
      setMessage(`ISBN ${isbn} を読み取りました。判定画面へ移動します...`);
      if (active) {
        navigate(`/result/${isbn}`);
      }
    };

    const start = async (): Promise<void> => {
      if (!videoRef.current) {
        setMessage("カメラの準備ができませんでした。ISBN を手入力してください。");
        setCameraUnavailable(true);
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
              width: { ideal: 1920 },
              height: { ideal: 1080 },
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
              setMessage("読み取り中に問題が発生しました。少し離して、明るい場所で試してください。");
            }
          },
        );

        controlsRef.current = controls;
        setCameraUnavailable(false);
        setMessage("バーコードを枠の中央に合わせてください。");
      } catch (error) {
        const detail = error instanceof Error ? error.message : String(error);
        if (/Permission|denied|NotAllowed/i.test(detail)) {
          setCameraUnavailable(true);
          setMessage("カメラの利用が許可されていません。ブラウザ設定で許可してください。");
          return;
        }
        if (/secure|https|origin/i.test(detail)) {
          setCameraUnavailable(true);
          setMessage("カメラは HTTPS または localhost の環境でのみ利用できます。");
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
            <h3>カメラで ISBN を読み取る</h3>
          </div>
        </div>

        <div className={`scanner-shell ${cameraUnavailable ? "is-unavailable" : ""}`}>
          <video ref={videoRef} className="scanner-video" muted playsInline autoPlay />
          <div className="scanner-overlay" aria-hidden="true">
            <div className="scanner-target" />
          </div>
        </div>

        <p className={`subtle ${cameraUnavailable ? "scan-unavailable" : ""}`}>{message}</p>

        <div className="scan-manual">
          <label>
            ISBN を手入力
            <input
              value={isbnInput}
              onChange={(event) => setIsbnInput(event.target.value)}
              placeholder="9784860648114"
              inputMode="numeric"
              aria-label="ISBN を手入力"
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

        <ul className="scan-tips">
          <li>バーコードを横向きのまま枠に合わせてください。</li>
          <li>近づきすぎると読み取りにくくなるため、少し離して試してください。</li>
          <li>影が入らない明るい場所で固定すると反応しやすくなります。</li>
        </ul>
      </section>
    </AppLayout>
  );
}
