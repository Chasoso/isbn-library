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
  const [message, setMessage] = useState(
    "裏表紙の ISBN バーコードを枠に合わせてください。読み取り後は自動で判定画面に移動します。",
  );

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
        setMessage("ISBN バーコードとして認識できませんでした。少し角度を変えて再度お試しください。");
        return;
      }

      detected = true;
      controlsRef.current?.stop();
      setMessage(`ISBN ${isbn} を読み取りました。判定画面へ移動しています...`);
      if (active) {
        navigate(`/result/${isbn}`);
      }
    };

    const start = async (): Promise<void> => {
      if (!videoRef.current) {
        setMessage("スキャン画面の初期化に失敗しました。");
        return;
      }

      try {
        const devices = await BrowserMultiFormatReader.listVideoInputDevices();
        const preferredDevice =
          devices.find((device) => /back|rear|environment|背面/i.test(device.label)) ??
          devices[0];

        if (!preferredDevice) {
          setMessage("利用可能なカメラが見つかりません。");
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
              setMessage(`読み取り中にエラーが発生しました: ${error.message}`);
            }
          },
        );

        controlsRef.current = controls;
        setMessage(
          "バーコードを中央の枠に合わせてください。少し離して固定すると反応しやすくなります。",
        );
      } catch (error) {
        const detail = error instanceof Error ? error.message : String(error);
        if (/Permission|denied|NotAllowed/i.test(detail)) {
          setMessage(
            "カメラ権限が拒否されています。ブラウザ設定でカメラ利用を許可してください。",
          );
          return;
        }
        if (/secure|https|origin/i.test(detail)) {
          setMessage("カメラは HTTPS または localhost でのみ利用できます。");
          return;
        }
        setMessage(`カメラを利用できません: ${detail}`);
      }
    };

    void start();

    return () => {
      active = false;
      controlsRef.current?.stop();
      controlsRef.current = null;
    };
  }, [navigate]);

  return (
    <AppLayout title="スキャン" subtitle="いつでも書籍を登録できる常設アクション">
      <section className="panel scan-panel">
        <div className="section-heading">
          <div>
            <p className="section-label">ISBN スキャン</p>
            <h3>カメラで ISBN を読み取る</h3>
          </div>
        </div>
        <div className="scanner-shell">
          <video ref={videoRef} className="scanner-video" muted playsInline autoPlay />
          <div className="scanner-overlay" aria-hidden="true">
            <div className="scanner-target" />
          </div>
        </div>
        <p className="subtle">{message}</p>
        <ul className="scan-tips">
          <li>裏表紙の ISBN バーコードを横向きのまま枠に合わせてください。</li>
          <li>近づけすぎるとピントが合いにくいので、少し離した方が読みやすいです。</li>
          <li>影が入らない明るい場所で固定すると反応しやすくなります。</li>
        </ul>
      </section>
    </AppLayout>
  );
}
