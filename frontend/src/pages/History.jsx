import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import HistoryCard from "../components/HistoryCard";
import Loader from "../components/Loader";
import { getHistory, getStoredUser } from "../services/api";

function History() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  const fetchData = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await getHistory(20);
      if (response?.status === "success" && Array.isArray(response.data)) {
        setItems(response.data);
      } else {
        setItems([]);
      }
    } catch {
      setError("Failed to load history. Please check backend connectivity.");
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const loggedInUser = getStoredUser();
    setUser(loggedInUser);
    if (loggedInUser) {
      fetchData();
    } else {
      setLoading(false);
    }
  }, []);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1, delayChildren: 0.2 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  };

  const buttonVariants = {
    hover: { scale: 1.05, y: -2 },
    tap: { scale: 0.98 },
  };

  if (!user) {
    return (
      <motion.section
        className="history-page"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <motion.div
          className="login-prompt"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.p
            className="card empty-message"
            variants={itemVariants}
          >
            Login to view history
          </motion.p>
          <motion.button
            type="button"
            className="primary-btn"
            onClick={() => navigate("/login")}
            variants={buttonVariants}
            whileHover="hover"
            whileTap="tap"
          >
            Go to Login
          </motion.button>
        </motion.div>
      </motion.section>
    );
  }

  return (
    <motion.section
      className="history-page"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <motion.div
        className="history-head"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1>Prediction History</h1>
        <motion.button
          type="button"
          className="secondary-btn"
          onClick={fetchData}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.98 }}
        >
          Refresh
        </motion.button>
      </motion.div>
      {loading ? <Loader text="Loading history..." /> : null}
      {error ? (
        <motion.p
          className="form-error card"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {error}
        </motion.p>
      ) : null}
      {!loading && !error && items.length === 0 ? (
        <motion.p
          className="card empty-message"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          No history found yet.
        </motion.p>
      ) : null}
      <motion.div
        className="history-list"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {items.map((item) => (
          <HistoryCard key={item.id || `${item.file_name}-${item.timestamp}`} item={item} />
        ))}
      </motion.div>
    </motion.section>
  );
}

export default History;
