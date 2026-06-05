import { motion } from "framer-motion";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { clearStoredUser, getStoredUser } from "../services/api";

function Navbar() {
  const navigate = useNavigate();
  const user = getStoredUser();

  const handleLogout = () => {
    clearStoredUser();
    navigate("/login");
  };

  const navItemVariants = {
    hidden: { opacity: 0, y: -10 },
    visible: (i) => ({
      opacity: 1,
      y: 0,
      transition: { delay: i * 0.05, duration: 0.3 },
    }),
  };

  return (
    <header className="navbar">
      <motion.div
        className="container navbar-content"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        <motion.div
          variants={navItemVariants}
          initial="hidden"
          animate="visible"
          custom={0}
        >
          <Link to="/" className="brand">
            Deepfake Detection AI
          </Link>
        </motion.div>
        <nav className="nav-links">
          <motion.div
            variants={navItemVariants}
            initial="hidden"
            animate="visible"
            custom={1}
          >
            <NavLink to="/" end>
              Home
            </NavLink>
          </motion.div>
          <motion.div
            variants={navItemVariants}
            initial="hidden"
            animate="visible"
            custom={2}
          >
            <NavLink to="/history">History</NavLink>
          </motion.div>
          {user ? (
            <motion.button
              className="ghost-btn"
              onClick={handleLogout}
              type="button"
              variants={navItemVariants}
              initial="hidden"
              animate="visible"
              custom={3}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Logout ({user.username})
            </motion.button>
          ) : (
            <>
              <motion.div
                variants={navItemVariants}
                initial="hidden"
                animate="visible"
                custom={3}
              >
                <NavLink to="/login">Login</NavLink>
              </motion.div>
              <motion.div
                variants={navItemVariants}
                initial="hidden"
                animate="visible"
                custom={4}
              >
                <NavLink to="/register">Register</NavLink>
              </motion.div>
            </>
          )}
        </nav>
      </motion.div>
    </header>
  );
}

export default Navbar;
