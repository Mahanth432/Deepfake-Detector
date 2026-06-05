import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import AuthForm from "../components/AuthForm";
import OtpInput from "../components/OtpInput";
import {
  sendRegisterOtp,
  verifyRegisterOtp,
  setStoredUser,
} from "../services/api";
import { AnimatePresence, motion } from "framer-motion";

function Register() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState("");
  const [otpLoading, setOtpLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [countdown, setCountdown] = useState(300);
  const [pendingRegister, setPendingRegister] = useState(null);

  useEffect(() => {
    if (!otpSent) {
      setCountdown(300);
      return;
    }

    const timer = setInterval(() => {
      setCountdown((prev) => Math.max(prev - 1, 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [otpSent]);

  const formatCountdown = () => {
    const minutes = String(Math.floor(countdown / 60)).padStart(2, "0");
    const seconds = String(countdown % 60).padStart(2, "0");
    return `${minutes}:${seconds}`;
  };

  const handleRegister = async (values) => {
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const response = await sendRegisterOtp(values);
      if (response?.status === "success") {
        setPendingRegister(values);
        setOtpSent(true);
        setOtp("");
        setOtpError("");
        setSuccess("OTP sent successfully");
      } else {
        setError(response?.message || "Failed to send OTP.");
      }
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || "Could not send OTP. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (!pendingRegister) return;
    setOtpLoading(true);
    setOtpError("");

    try {
      const response = await verifyRegisterOtp({
        email: pendingRegister.email,
        otp,
      });
      if (response?.status === "success" && response.user) {
        setStoredUser(response.user);
        navigate("/");
      } else {
        setOtpError(response?.message || "OTP verification failed.");
      }
    } catch (requestError) {
      setOtpError(requestError?.response?.data?.detail || "Invalid OTP. Please try again.");
    } finally {
      setOtpLoading(false);
    }
  };

  const handleResend = async () => {
    if (!pendingRegister) {
      return;
    }
    setResendLoading(true);
    setOtpError("");
    setSuccess("");
    try {
      await sendRegisterOtp(pendingRegister);
      setCountdown(300);
      setSuccess("OTP sent successfully");
    } catch (requestError) {
      setOtpError(requestError?.response?.data?.detail || "Unable to resend OTP.");
    } finally {
      setResendLoading(false);
    }
  };

  const closeOtpModal = () => {
    setOtpSent(false);
    setOtp("");
    setOtpError("");
  };

  return (
    <section className="auth-page">
      <AuthForm mode="register" onSubmit={handleRegister} loading={loading} error={error} success={success} />
      <p className="auth-redirect">
        Already have an account? <Link to="/login">Login now</Link>
      </p>

      <AnimatePresence>
        {otpSent && (
          <motion.div
            className="auth-modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeOtpModal}
          >
            <motion.div
              className="auth-modal-card"
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.94 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              onClick={(event) => event.stopPropagation()}
            >
              <button className="modal-close-btn" type="button" onClick={closeOtpModal}>
                &times;
              </button>
              <div className="auth-modal-header">
                <h2>Verify your email</h2>
                <p>Enter the 6-digit code sent to {pendingRegister?.email}</p>
              </div>

              <OtpInput value={otp} onChange={setOtp} disabled={otpLoading} />

              <div className="otp-meta-row">
                <span>Expires in {formatCountdown()}</span>
                <button
                  type="button"
                  className="ghost-btn otp-resend-btn"
                  onClick={handleResend}
                  disabled={resendLoading}
                >
                  {resendLoading ? "Resending..." : "Resend OTP"}
                </button>
              </div>
              {otpError ? <p className="form-error">{otpError}</p> : null}
              <button
                type="button"
                className="primary-btn"
                onClick={handleVerifyOtp}
                disabled={otpLoading || otp.length < 6}
              >
                {otpLoading ? "Verifying..." : "Confirm OTP"}
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}

export default Register;
