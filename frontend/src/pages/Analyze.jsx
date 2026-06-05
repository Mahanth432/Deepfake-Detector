import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  LucideUploadCloud,
  LucideArrowRight,
  LucideCheckCircle,
  LucideAlertTriangle,
  LucideShieldCheck,
  LucideSparkles,
  LucideGauge,
} from "lucide-react";
import { predictImage } from "../services/api";
import { getDisplayConfidence } from "../utils/confidence";
import Loader from "../components/Loader";
import sampleImage from "../../images/image.webp";

function Analyze() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return;
    }

    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    return () => URL.revokeObjectURL(url);
  }, [file]);

  const processFile = (incomingFile) => {
    if (!incomingFile) return;
    if (!incomingFile.type.startsWith("image/")) {
      setError("Please upload a valid image file.");
      return;
    }

    setError("");
    setResult(null);
    setFile(incomingFile);
  };

  const handleFileChange = (event) => {
    processFile(event.target.files?.[0]);
  };

  const handleAnalyze = async () => {
    if (!file) {
      setError("Choose an image before analyzing.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const response = await predictImage(file);
      if (response?.status === "success") {
        setResult(response);
      } else {
        setError(response?.message || "Analysis failed.");
      }
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          "Unable to connect to the backend."
      );
    } finally {
      setLoading(false);
    }
  };

  const resetPage = () => {
    setFile(null);
    setPreviewUrl("");
    setResult(null);
    setError("");
    if (inputRef.current) {
      inputRef.current.value = null;
    }
  };

  const predictionLabel = result?.prediction || "Unknown";
  const displayConfidence = getDisplayConfidence(predictionLabel, result?.confidence_score);
  const confidenceStr = displayConfidence.toFixed(2);
  const isFake = predictionLabel.toLowerCase() === "fake";
  const tone = isFake ? "danger" : "success";
  const confidenceWidth = `${Math.min(100, Math.max(0, displayConfidence))}%`;
  const statusHeadline = isFake
    ? "Potential manipulation detected"
    : "Image appears authentic";
  const previewLabel = result ? "Analysis Result" : "Image Preview";

  return (
    <div className="analyze-page">
      <div className="grid-bg" />

      <motion.section
        className="analyze-shell"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: "easeOut" }}
      >
        <motion.div
          className="analyze-card analyze-left"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.45, ease: "easeOut" }}
        >
          <div className="analyze-hero">
            <span className="result-badge">Analyze</span>
            <h2 className="analyze-title">Deepfake Detection Studio</h2>
            <p className="analyze-copy">
              Upload a photo, run detection, and review the prediction in a
              fixed dashboard layout.
            </p>
          </div>

          <motion.div
            className={`analyze-dropzone ${file ? "has-file" : ""}`}
            onClick={() => inputRef.current?.click()}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
          >
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              hidden
              onChange={handleFileChange}
            />

            {!previewUrl ? (
              <div className="analyze-drop-text">
                <LucideUploadCloud size={48} />
                <h3>Select an image to analyze</h3>
                <p>Tap or drag an image to inspect AI manipulation.</p>
              </div>
            ) : (
              <motion.img
                src={previewUrl}
                alt="Uploaded preview"
                className="analyze-preview"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
              />
            )}
          </motion.div>

          <div className="analyze-actions-row">
            <button
              type="button"
              className="primary-btn"
              onClick={handleAnalyze}
              disabled={loading}
            >
              {loading ? "Analyzing..." : "Analyze Image"}
              <LucideArrowRight size={16} style={{ marginLeft: "0.5rem" }} />
            </button>
          </div>

          {error && (
            <motion.p
              className="form-error card fade-in"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <LucideAlertTriangle size={18} /> {error}
            </motion.p>
          )}

          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="card analyze-status"
            >
              <Loader text="Analyzing image..." />
            </motion.div>
          )}
        </motion.div>

        <motion.div
          className="analyze-card analyze-right"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.45, ease: "easeOut" }}
        >
          <article className="card analyze-info sample-panel">
            <h3>Sample Deepfake Comparison</h3>
            <p>
              Reference imagery and label guidance show the kind of manipulation
              the model catches.
            </p>
            <img src={sampleImage} alt="Sample deepfake analysis" />
            <div className="sample-status-grid">
              <span className="sample-pill success">Authentic style</span>
              <span className="sample-pill danger">Manipulated style</span>
            </div>
          </article>
        </motion.div>
      </motion.section>

      {result ? (
        <motion.div
          className={`analyze-result-bar ${tone}`}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: "easeOut" }}
        >
          <div className="result-section result-prediction-section">
            <div className="result-section-header">
              <LucideSparkles size={18} />
              <span>Prediction</span>
            </div>
            <p className={`result-prediction ${tone}`}>{predictionLabel}</p>
          </div>

          <div className="result-section result-confidence-section">
            <div className="result-section-header">
              <LucideGauge size={18} />
              <span>Confidence</span>
            </div>
            <p className="confidence-value">{confidenceStr}%</p>
          </div>

          <div className="result-section result-status-section">
            <div className="result-section-header">
              <LucideShieldCheck size={18} />
              <span>Status</span>
            </div>
            <p className="result-status-text">{statusHeadline}</p>
          </div>

          <div className="result-progress-section">
            <div className="progress-meta">
              <span>Progress</span>
              <span>{confidenceStr}%</span>
            </div>
            <div className="confidence-track progress-bar">
              <div
                className={`confidence-fill ${tone}`}
                style={{ width: confidenceWidth }}
              />
            </div>
            <button
              className="secondary-btn result-action-btn"
              type="button"
              onClick={resetPage}
            >
              Analyze another image
            </button>
          </div>
        </motion.div>
      ) : null}
    </div>
  );
}

export default Analyze;
