import { motion } from "framer-motion";
import { getDisplayConfidence } from "../utils/confidence";

function HistoryCard({ item }) {
  const prediction = item.prediction || "Unknown";
  const displayConfidence = getDisplayConfidence(prediction, item.confidence_score);
  const confidenceStr = displayConfidence.toFixed(2);
  const tone = prediction.toLowerCase() === "fake" ? "danger" : "success";
  const date = item.timestamp ? new Date(item.timestamp).toLocaleString() : "Unknown date";
  const imgSrc = item.image_base64
    ? `data:${item.mime_type || "image/jpeg"};base64,${item.image_base64}`
    : null;

  const cardVariants = {
    hidden: { opacity: 0, x: -20 },
    visible: {
      opacity: 1,
      x: 0,
      transition: { duration: 0.3, ease: "easeOut" },
    },
  };

  const imageVariants = {
    hover: {
      scale: 1.05,
      transition: { type: "spring", stiffness: 400, damping: 10 },
    },
  };

  return (
    <motion.article
      className={`card history-card ${tone}`}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      whileHover={{ x: 8 }}
    >
      <div className="history-thumb-wrap">
        {imgSrc ? (
          <motion.img
            src={imgSrc}
            alt={item.file_name || "History item"}
            className="history-thumb"
            variants={imageVariants}
            whileHover="hover"
          />
        ) : (
          <div className="history-fallback">No Preview</div>
        )}
      </div>
      <div className="history-meta">
        <div className="history-meta-top">
          <h3>{item.file_name || "Unknown file"}</h3>
          {item.duplicate ? <span className="duplicate-badge">Duplicate</span> : null}
        </div>
        <p>{date}</p>
      </div>
      <div className="history-result">
        <span className={tone}>{prediction}</span>
        <small>{confidenceStr}% confidence</small>
      </div>
    </motion.article>
  );
}

export default HistoryCard;
