import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  LucideSparkles,
  LucideBarChart2,
  LucideShieldCheck,
  LucideX,
  LucideClock,
  LucideCpu,
  LucideDatabase,
} from "lucide-react";

const featureCards = [
  {
    id: "accuracy",
    title: "93.12% Accuracy",
    icon: LucideBarChart2,
    modalTitle: "93.12% Detection Accuracy",
    modalItems: [
      "Vision Transformer (ViT-B/16) backbone architecture",
      "High classification accuracy on GRAVEX-200K benchmark",
      "Optimized for low false positive rates (94.58% Precision)",
      "Robust class-separation boundary under varying compressions",
      "Verified on 30,000 independent test images",
    ],
    modalIcon: LucideBarChart2,
  },
  {
    id: "speed",
    title: "Efficient Inference",
    icon: LucideClock,
    modalTitle: "Optimized Inference Speed",
    modalItems: [
      "Fast image preprocessing pipeline",
      "Inference wrapper supporting standard CPU/GPU execution",
      "Highly responsive API integration for seamless analysis",
      "Instant upload-to-result prediction workflow",
    ],
    modalIcon: LucideClock,
  },
  {
    id: "vit",
    title: "ViT-B/16 Backbone",
    icon: LucideCpu,
    modalTitle: "Vision Transformer Model Details",
    modalItems: [
      "Uses 12 transformer blocks with 12 attention heads each",
      "Splits input images into 16x16 non-overlapping patches",
      "Pretrained on ImageNet-21k for robust feature representations",
      "Fine-tuned specifically on synthetic generation artifacts",
      "Partial backbone unfreezing: last 4 blocks updated during training",
    ],
    modalIcon: LucideCpu,
  },
  {
    id: "dataset",
    title: "GRAVEX-200K Dataset",
    icon: LucideDatabase,
    modalTitle: "Dataset Composition & Splits",
    modalItems: [
      "Total dataset size of 200,000 high-resolution images",
      "Training set: 140,000 images (70%)",
      "Validation set: 30,000 images (15%)",
      "Test set: 30,000 images (15%)",
      "Covers diverse GAN, diffusion, and autoregressive models",
    ],
    modalIcon: LucideDatabase,
  },
];

function Home() {
  const [activeFeature, setActiveFeature] = useState(null);
  const navigate = useNavigate();

  const fadeUp = {
    hidden: { opacity: 0, y: 24 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.55, ease: "easeOut" },
    },
  };

  const openFeature = (feature) => setActiveFeature(feature);
  const closeFeature = () => setActiveFeature(null);

  return (
    <div className="home-page">
      <div className="grid-bg" />

      <section className="hero-section home-hero">
        <motion.div
          className="hero-text"
          variants={fadeUp}
          initial="hidden"
          animate="visible"
        >
          <h1>
            AI-Generated Image Detection.
            <br />
            Powered by Vision Transformers.
          </h1>

          <p>
            Deploying a fine-tuned ViT-B/16 model trained on the GRAVEX-200K dataset,
            achieving a verified 93.12% test accuracy in identifying AI-generated manipulations.
          </p>

          <div className="hero-buttons hero-actions">
            <button
              className="primary-btn"
              onClick={() => navigate("/analyze")}
            >
              Analyze Image
            </button>
          </div>
        </motion.div>
      </section>

      <section id="stats" className="stats-section">
        <div className="stats-grid">
          {featureCards.map((card, index) => {
            const Icon = card.icon;
            return (
              <motion.div
                key={card.id}
                className="card stat-card interactive-card"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 + index * 0.1 }}
                onClick={() => openFeature(card)}
              >
                <Icon size={36} className="stat-icon" />
                <h3>{card.title}</h3>
              </motion.div>
            );
          })}
        </div>
      </section>

      <section className="features-section">
        <div className="features-grid">
          <motion.div
            className="card feature-card"
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.15 }}
          >
            <LucideCpu size={40} />
            <h3>ViT-B/16 Self-Attention</h3>
            <p>
              Utilizes multi-head self-attention mechanisms to map global image patches
              and detect subtle, non-local synthetic artifacts.
            </p>
          </motion.div>

          <motion.div
            className="card feature-card"
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.25 }}
          >
            <LucideDatabase size={40} />
            <h3>GRAVEX-200K Benchmark</h3>
            <p>
              Trained on 200,000 diverse images featuring advanced GAN, diffusion, and
              transformer-based generator architectures.
            </p>
          </motion.div>

          <motion.div
            className="card feature-card"
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.35 }}
          >
            <LucideSparkles size={40} />
            <h3>Transfer & Fine-Tuning</h3>
            <p>
              Leverages pre-trained representation capabilities while unfreezing the last 
              4 transformer blocks for precise domain adaptation.
            </p>
          </motion.div>
        </div>
      </section>

      <section className="model-insights-section">
        <div className="insights-header">
          <h2>Technical Specifications & Performance Evaluation</h2>
          <p>Detailed architectural configuration and verified test metrics from the GRAVEX-200K evaluation.</p>
        </div>

        <div className="insights-grid">
          <motion.div
            className="card insight-card"
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <h3>Model Details & Hyperparameters</h3>
            <div className="details-list">
              <div className="detail-row">
                <span className="detail-label">Model Architecture</span>
                <span className="detail-value">Vision Transformer (ViT-B/16)</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Pre-trained Dataset</span>
                <span className="detail-value">ImageNet-21k (14M images)</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Target Dataset</span>
                <span className="detail-value">GRAVEX-200K (200,000 images)</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Training Size</span>
                <span className="detail-value">140,000 Images</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Validation Size</span>
                <span className="detail-value">30,000 Images</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Test Size</span>
                <span className="detail-value">30,000 Images</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Adaptation Method</span>
                <span className="detail-value">Transfer Learning + Fine-Tuning</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Unfrozen Backbone</span>
                <span className="detail-value">Last 4 Transformer Blocks</span>
              </div>
            </div>
          </motion.div>

          <motion.div
            className="card insight-card"
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <h3>Verified Test Evaluation Metrics</h3>
            <div className="metrics-wrapper">
              <div className="metric-progress-item">
                <div className="metric-progress-header">
                  <span className="metric-title">Accuracy</span>
                  <span className="metric-pct">93.12%</span>
                </div>
                <div className="metric-progress-track">
                  <div className="metric-progress-fill accent-blue" style={{ width: "93.12%" }} />
                </div>
                <p className="metric-desc">Overall correctness rate on 30,000 independent test images.</p>
              </div>

              <div className="metric-progress-item">
                <div className="metric-progress-header">
                  <span className="metric-title">Precision</span>
                  <span className="metric-pct">94.58%</span>
                </div>
                <div className="metric-progress-track">
                  <div className="metric-progress-fill accent-purple" style={{ width: "94.58%" }} />
                </div>
                <p className="metric-desc">Accuracy of positive predictions; measures the model's resistance to false alarms.</p>
              </div>

              <div className="metric-progress-item">
                <div className="metric-progress-header">
                  <span className="metric-title">Recall (Sensitivity)</span>
                  <span className="metric-pct">91.47%</span>
                </div>
                <div className="metric-progress-track">
                  <div className="metric-progress-fill accent-teal" style={{ width: "91.47%" }} />
                </div>
                <p className="metric-desc">Percentage of actual AI manipulations correctly identified by the model.</p>
              </div>

              <div className="metric-progress-item">
                <div className="metric-progress-header">
                  <span className="metric-title">F1 Score</span>
                  <span className="metric-pct">93.00%</span>
                </div>
                <div className="metric-progress-track">
                  <div className="metric-progress-fill accent-pink" style={{ width: "93.00%" }} />
                </div>
                <p className="metric-desc">Harmonic mean of precision and recall, balancing classification quality.</p>
              </div>

              <div className="metric-progress-item">
                <div className="metric-progress-header">
                  <span className="metric-title">ROC-AUC</span>
                  <span className="metric-pct">0.9874</span>
                </div>
                <div className="metric-progress-track">
                  <div className="metric-progress-fill accent-indigo" style={{ width: "98.74%" }} />
                </div>
                <p className="metric-desc">Area Under the ROC Curve; evaluates discrimination capability across all thresholds.</p>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <AnimatePresence>
        {activeFeature && (
          <motion.div
            className="feature-modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeFeature}
          >
            <motion.div
              className="feature-modal-card"
              initial={{ opacity: 0, scale: 0.92 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.92 }}
              transition={{ duration: 0.28, ease: "easeOut" }}
              onClick={(event) => event.stopPropagation()}
            >
              <button
                className="modal-close-btn"
                type="button"
                onClick={closeFeature}
              >
                <LucideX size={18} />
              </button>
              <div className="modal-title-row">
                <activeFeature.modalIcon
                  size={24}
                  className="modal-title-icon"
                />
                <div>
                  <p className="modal-subtitle">Feature details</p>
                  <h2>{activeFeature.modalTitle}</h2>
                </div>
              </div>

              <div className="modal-content">
                <ul className="modal-bullet-list">
                  {activeFeature.modalItems.map((item) => (
                    <li key={item} className="modal-list-item">
                      <LucideSparkles size={16} className="modal-list-icon" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default Home;
