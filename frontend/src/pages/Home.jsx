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
  LucideShield,
} from "lucide-react";

const featureCards = [
  {
    id: "accuracy",
    title: "98.9% Accuracy",
    icon: LucideBarChart2,
    modalTitle: "98.9% Detection Accuracy",
    modalItems: [
      "Model trained using Vision Transformer (ViT)",
      "High precision deepfake classification",
      "Tested on real and manipulated datasets",
      "Optimized for low false positives",
      "Reliable confidence scoring",
    ],
    modalIcon: LucideBarChart2,
  },
  {
    id: "speed",
    title: "<2s Detection",
    icon: LucideSparkles,
    modalTitle: "Real-Time Detection",
    modalItems: [
      "Prediction generated in under 2 seconds",
      "Fast preprocessing pipeline",
      "Optimized PyTorch inference",
      "Lightweight backend architecture",
      "Instant upload-to-result workflow",
    ],
    modalIcon: LucideClock,
  },
  {
    id: "vit",
    title: "ViT Transformer",
    icon: LucideBarChart2,
    modalTitle: "Vision Transformer Architecture",
    modalItems: [
      "Uses Google ViT-B/16 pretrained model",
      "Captures global image relationships",
      "Better than CNNs for subtle manipulations",
      "Patch embedding + self-attention mechanism",
      "Improved deepfake feature learning",
    ],
    modalIcon: LucideCpu,
  },
  {
    id: "secure",
    title: "Secure Analysis",
    icon: LucideShieldCheck,
    modalTitle: "Secure & Private Analysis",
    modalItems: [
      "User-based private history",
      "Secure MongoDB storage",
      "Duplicate protection per account",
      "No cross-user data exposure",
      "Protected authentication workflow",
    ],
    modalIcon: LucideShield,
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
            Detect AI Manipulation.
            <br />
            Protect Digital Truth.
          </h1>

          <p>
            Advanced Vision Transformer powered deepfake detection
            with real-time AI analysis.
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
            <LucideSparkles size={40} />
            <h3>Vision Transformer Detection</h3>
            <p>
              State-of-the-art ViT model identifies deepfakes with
              precision.
            </p>
          </motion.div>

          <motion.div
            className="card feature-card"
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.25 }}
          >
            <LucideBarChart2 size={40} />
            <h3>Real-time AI Analysis</h3>
            <p>Instant predictions delivered in under two seconds.</p>
          </motion.div>

          <motion.div
            className="card feature-card"
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.35 }}
          >
            <LucideShieldCheck size={40} />
            <h3>Secure Detection History</h3>
            <p>Your analyses are stored safely and privately.</p>
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
