import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import AuthForm from "../components/AuthForm";
import OtpInput from "../components/OtpInput";
import {
  login,
  setStoredUser,
  forgotPassword,
  verifyResetOtp,
  resetPassword,
} from "../services/api";
import { AnimatePresence, motion } from "framer-motion";

function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [forgotOpen, setForgotOpen] = useState(false);
  const [forgotStep, setForgotStep] = useState(1);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotError, setForgotError] = useState("");
  const [forgotSuccess, setForgotSuccess] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [otp, setOtp] = useState("");
  const [otpLoading, setOtpLoading] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [countdown, setCountdown] = useState(300);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  useEffect(() => {
    if (!forgotOpen || forgotStep !== 2) {
      return undefined;
    }

    const timer = setInterval(() => {
      setCountdown((prev) => Math.max(prev - 1, 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [forgotOpen, forgotStep]);

  const formatCountdown = () => {
    const minutes = String(Math.floor(countdown / 60)).padStart(2, "0");
    const seconds = String(countdown % 60).padStart(2, "0");
    return `${minutes}:${seconds}`;
  };

  const handleLogin = async (values) => {
    setLoading(true);
    setError("");
    try {
      const response = await login({ email: values.email, password: values.password });
      if (response?.status === "success" && response.user) {
        setStoredUser(response.user);
        navigate("/");
      } else {
        setError("Login failed.");
      }
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || "Could not login. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const openForgot = () => {
    setForgotOpen(true);
    setForgotStep(1);
    setForgotEmail("");
    setForgotError("");
    setForgotSuccess("");
    setOtp("");
    setNewPassword("");
    setConfirmPassword("");
    setCountdown(300);
  };

  const closeForgot = () => {
    setForgotOpen(false);
    setForgotStep(1);
    setForgotError("");
    setForgotSuccess("");
    setOtp("");
    setCountdown(300);
  };

  const handleForgotSend = async () => {
    setForgotLoading(true);
    setForgotError("");
    setForgotSuccess("");

    try {
      const response = await forgotPassword({ email: forgotEmail });
      if (response?.status === "success") {
        setForgotStep(2);
        setOtp("");
        setCountdown(300);
        setForgotSuccess("OTP sent successfully");
      } else {
        setForgotError(response?.message || "Failed to send OTP.");
      }
    } catch (requestError) {
      setForgotError(requestError?.response?.data?.detail || "Could not send OTP. Try again.");
    } finally {
      setForgotLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    setOtpLoading(true);
    setForgotError("");
    try {
      const response = await verifyResetOtp({ email: forgotEmail, otp });
      if (response?.status === "success") {
        setForgotStep(3);
      } else {
        setForgotError(response?.message || "OTP verification failed.");
      }
    } catch (requestError) {
      setForgotError(requestError?.response?.data?.detail || "Invalid OTP. Please try again.");
    } finally {
      setOtpLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setForgotLoading(true);
    setForgotError("");
    try {
      await forgotPassword({ email: forgotEmail });
      setCountdown(300);
    } catch (requestError) {
      setForgotError(requestError?.response?.data?.detail || "Unable to resend OTP.");
    } finally {
      setForgotLoading(false);
    }
  };

  const handleResetPassword = async () => {
    if (newPassword !== confirmPassword) {
      setForgotError("Passwords do not match.");
      return;
    }

    setResetLoading(true);
    setForgotError("");
    try {
      const response = await resetPassword({
        email: forgotEmail,
        otp,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      if (response?.status === "success") {
        closeForgot();
        setError("Password reset successfully. Please login with your new password.");
      } else {
        setForgotError(response?.message || "Unable to reset password.");
      }
    } catch (requestError) {
      setForgotError(requestError?.response?.data?.detail || "Password reset failed.");
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <section className="auth-page">
      <AuthForm mode="login" onSubmit={handleLogin} loading={loading} error={error} />
      <p className="auth-redirect">
        New user? <Link to="/register">Create an account</Link>
      </p>
      <div className="forgot-password-wrapper">
  <button
    type="button"
    className="ghost-btn forgot-password-link"
    onClick={openForgot}
  >
    Forgot Password?
  </button>
</div>

      <AnimatePresence>
        {forgotOpen && (
          <motion.div
            className="auth-modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeForgot}
          >
            <motion.div
              className="auth-modal-card"
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.94 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              onClick={(event) => event.stopPropagation()}
            >
              <button className="modal-close-btn" type="button" onClick={closeForgot}>
                &times;
              </button>
              <div className="auth-modal-header">
                {forgotStep === 1 && <h2>Reset your password</h2>}
                {forgotStep === 2 && <h2>Enter OTP code</h2>}
                {forgotStep === 3 && <h2>Choose a new password</h2>}
                <p>
                  {forgotStep === 1 && "Enter your registered email to receive a reset code."}
                  {forgotStep === 2 && `A 6-digit OTP was sent to ${forgotEmail}.`}
                  {forgotStep === 3 && "Set a secure new password for your account."}
                </p>
              </div>

              {forgotStep === 1 && (
                <div className="auth-modal-form">
                  <label htmlFor="forgotEmail">Email</label>
                  <input
                    id="forgotEmail"
                    type="email"
                    placeholder="Enter your registered email"
                    value={forgotEmail}
                    onChange={(event) => setForgotEmail(event.target.value)}
                    required
                  />
                  <button
                    type="button"
                    className={`primary-btn ${forgotLoading ? "loading" : ""}`}
                    onClick={handleForgotSend}
                    disabled={forgotLoading || !forgotEmail}
                  >
                    {forgotLoading ? "Sending OTP..." : "Send OTP"}
                  </button>
                </div>
              )}

              {forgotStep === 2 && (
                <>
                  <OtpInput value={otp} onChange={setOtp} disabled={otpLoading} />
                  <div className="otp-meta-row">
                    <span>Expires in {formatCountdown()}</span>
                    <button
                      type="button"
                      className="ghost-btn otp-resend-btn"
                      onClick={handleResendOtp}
                      disabled={forgotLoading}
                    >
                      {forgotLoading ? "Resending..." : "Resend OTP"}
                    </button>
                  </div>
                  <button
                    type="button"
                    className="primary-btn"
                    onClick={handleVerifyOtp}
                    disabled={otpLoading || otp.length < 6}
                  >
                    {otpLoading ? "Verifying..." : "Verify OTP"}
                  </button>
                </>
              )}

              {forgotStep === 3 && (
                <div className="auth-modal-form">
                  <label htmlFor="resetPassword">New Password</label>
                  <div className="password-input-container">
                    <input
                      id="resetPassword"
                      type={showNewPassword ? "text" : "password"}
                      placeholder="New password"
                      value={newPassword}
                      onChange={(event) => setNewPassword(event.target.value)}
                      required
                    />
                    <button
                      type="button"
                      className="password-toggle-btn"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      aria-label={showNewPassword ? "Hide password" : "Show password"}
                      tabIndex="-1"
                    >
                      {showNewPassword ? "🙈" : "👁️"}
                    </button>
                  </div>
                  <label htmlFor="confirmResetPassword">Confirm Password</label>
                  <div className="password-input-container">
                    <input
                      id="confirmResetPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      placeholder="Confirm password"
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      required
                    />
                    <button
                      type="button"
                      className="password-toggle-btn"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                      tabIndex="-1"
                    >
                      {showConfirmPassword ? "🙈" : "👁️"}
                    </button>
                  </div>
                  <button
                    type="button"
                    className={`primary-btn ${resetLoading ? "loading" : ""}`}
                    onClick={handleResetPassword}
                    disabled={resetLoading || !newPassword || !confirmPassword}
                  >
                    {resetLoading ? "Resetting..." : "Reset Password"}
                  </button>
                </div>
              )}

              {forgotError ? <p className="form-error">{forgotError}</p> : null}
              {forgotSuccess ? <p className="form-success">{forgotSuccess}</p> : null}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}

export default Login;
