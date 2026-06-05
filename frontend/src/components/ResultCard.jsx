import { motion } from "framer-motion";
import { getDisplayConfidence } from "../utils/confidence";

function ResultCard({ result, onReset }) {
  if (!result) return null;

  const prediction = result.prediction || "Unknown";
  const displayConfidence = getDisplayConfidence(prediction, result.confidence_score);
  const confidenceStr = displayConfidence.toFixed(2);
  const tone = prediction.toLowerCase() === "fake" ? "danger" : "success";

  const containerVariants = {
    hidden: { opacity: 0, scale: 0.8, y: 20 },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      transition: { duration: 0.5, ease: "easeOut" },
    },
  };

  const textVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: (i) => ({
      opacity: 1,
      y: 0,
      transition: { delay: i * 0.1, duration: 0.4 },
    }),
  };

  const progressVariants = {
    hidden: { width: 0 },
    visible: {
      width: `${confidenceStr}%`,
      transition: { duration: 1, ease: "easeOut", delay: 0.3 },
    },
  };

  return (
    <motion.section
      className={`card result-card ${tone}`}
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.h2 variants={textVariants} custom={0} initial="hidden" animate="visible">
        Prediction Result
      </motion.h2>
      {result.duplicate ? (
        <motion.p
          className="info-banner"
          variants={textVariants}
          custom={1}
          initial="hidden"
          animate="visible"
        >
          This image was analyzed earlier. Showing saved result.
        </motion.p>
      ) : null}
      <motion.p
        className={`result-text ${tone}`}
        variants={textVariants}
        custom={2}
        initial="hidden"
        animate="visible"
      >
        {prediction}
      </motion.p>
      <div className="progress-track">
        <motion.div
          className={`progress-fill ${tone}`}
          variants={progressVariants}
          initial="hidden"
          animate="visible"
        />
      </div>
      <motion.p
        className="confidence-line"
        variants={textVariants}
        custom={3}
        initial="hidden"
        animate="visible"
      >
        Confidence: {confidenceStr}%
      </motion.p>
      <motion.button
        type="button"
        className="secondary-btn"
        onClick={onReset}
        whileHover={{ scale: 1.02, y: -2 }}
        whileTap={{ scale: 0.98 }}
        variants={textVariants}
        custom={4}
        initial="hidden"
        animate="visible"
      >
        Start New Analysis
      </motion.button>
    </motion.section>
  );
}

export default ResultCard;
