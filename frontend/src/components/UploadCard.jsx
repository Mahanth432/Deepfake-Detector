import React, { useRef, useState, useEffect } from "react";
import { motion, useAnimation } from "framer-motion";
import { Upload, X } from "lucide-react";

function UploadCard({ onFileSelect, selectedFile, previewUrl, onClear, onAnalyze, loading }) {
  const fileInputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const controls = useAnimation();

  // Simulate upload progress while loading
  useEffect(() => {
    if (loading) {
      setProgress(0);
      controls.start({ width: "100%", transition: { duration: 2, ease: "linear" } });
    } else {
      setProgress(0);
      controls.set({ width: 0 });
    }
  }, [loading, controls]);

  const processFile = (file) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      window.alert("Please upload an image file.");
      return;
    }
    onFileSelect(file);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    processFile(e.dataTransfer.files?.[0]);
  };

  const cardVariants = {
    hover: {
      y: -8,
      boxShadow: "0 20px 50px rgba(59, 130, 246, 0.3), 0 0 30px rgba(96, 165, 250, 0.2)",
    },
  };

  const iconVariants = {
    animate: {
      y: [0, -10, 0],
      transition: { duration: 3, repeat: Infinity },
    },
  };

  const dropzoneVariants = {
    dragActive: {
      scale: 1.02,
      boxShadow: "0 0 20px rgba(96, 165, 250, 0.3)",
      borderColor: "rgba(96, 165, 250, 0.8)",
    },
  };

  const imageVariants = {
    hidden: { opacity: 0, scale: 0.9 },
    visible: { opacity: 1, scale: 1, transition: { duration: 0.3 } },
    exit: { opacity: 0, scale: 0.9 },
  };

  const buttonVariants = {
    hover: { scale: 1.03, y: -4 },
    tap: { scale: 0.98 },
  };

  return (
    <motion.section
      className="card upload-card glass"
      variants={cardVariants}
      whileHover="hover"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: "spring", stiffness: 300 }}
    >
      <h2>Upload &amp; Analyze</h2>
      {!selectedFile ? (
        <motion.div
          className={`dropzone ${isDragging ? "dragging" : ""}`}
          ref={fileInputRef}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          variants={dropzoneVariants}
          animate={isDragging ? "dragActive" : ""}
          transition={{ type: "spring", stiffness: 300 }}
        >
          <motion.div variants={iconVariants} animate="animate">
            <Upload size={48} className="icon-glow" />
          </motion.div>
          <p className="dropzone-title">Drag &amp; drop your image</p>
          <p className="dropzone-subtitle">or click to browse</p>
          <input
            type="file"
            accept="image/*"
            hidden
            onChange={(e) => processFile(e.target.files?.[0])}
          />
        </motion.div>
      ) : (
        <motion.div
          className="preview-wrap"
          variants={imageVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          <motion.img
            src={previewUrl}
            alt="Selected preview"
            className="preview-image"
            whileHover={{ scale: 1.02 }}
            transition={{ type: "spring", stiffness: 400, damping: 10 }}
          />
          <div className="preview-actions">
            <span className="file-name">{selectedFile.name}</span>
            <motion.button
              className="ghost-btn"
              type="button"
              onClick={onClear}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              <X size={20} /> Remove
            </motion.button>
          </div>
        </motion.div>
      )}
      <motion.button
        className="primary-btn"
        type="button"
        disabled={!selectedFile || loading}
        onClick={onAnalyze}
        variants={buttonVariants}
        whileHover={!loading && selectedFile ? "hover" : {}}
        whileTap={!loading && selectedFile ? "tap" : {}}
      >
        {loading ? "Analyzing..." : "Analyze Image"}
      </motion.button>
      {loading && (
        <div className="upload-progress">
          <motion.div className="progress-fill" animate={controls} />
        </div>
      )}
    </motion.section>
  );
}

export default UploadCard;



