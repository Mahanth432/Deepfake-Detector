import { useState } from "react";

function PasswordInput({
  name,
  placeholder,
  value,
  show,
  onToggle,
  handleChange,
}) {
  return (
    <div className="password-input-container">
      <input
        name={name}
        type={show ? "text" : "password"}
        placeholder={placeholder}
        value={value}
        onChange={handleChange}
        required
      />

      <button
        type="button"
        className="password-toggle-btn"
        onClick={onToggle}
        aria-label={show ? "Hide password" : "Show password"}
      >
        {show ? "🙈" : "👁️"}
      </button>
    </div>
  );
}

function AuthForm({ mode, onSubmit, loading, error, success }) {
  const isRegister = mode === "register";

  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    confirm_password: "",
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();

    if (isRegister && form.password !== form.confirm_password) {
      window.alert("Passwords do not match.");
      return;
    }

    onSubmit(form);
  };

  return (
    <form className="card auth-card fade-in" onSubmit={handleSubmit}>
      <h2>{isRegister ? "Create your account" : "Welcome back"}</h2>

      <p className="auth-subtitle">
        {isRegister
          ? "Register to keep personal deepfake analysis history."
          : "Sign in to continue your deepfake analysis workflow."}
      </p>

      {isRegister && (
        <input
          name="username"
          placeholder="Username"
          value={form.username}
          onChange={handleChange}
          required
        />
      )}

      <input
        name="email"
        type="email"
        placeholder="Email"
        value={form.email}
        onChange={handleChange}
        required
      />

      <PasswordInput
        name="password"
        placeholder="Password"
        value={form.password}
        show={showPassword}
        onToggle={() => setShowPassword((prev) => !prev)}
        handleChange={handleChange}
      />

      {isRegister && (
        <PasswordInput
          name="confirm_password"
          placeholder="Confirm Password"
          value={form.confirm_password}
          show={showConfirmPassword}
          onToggle={() => setShowConfirmPassword((prev) => !prev)}
          handleChange={handleChange}
        />
      )}

      {error && <p className="form-error">{error}</p>}
      {success && <p className="form-success">{success}</p>}

      <button
        type="submit"
        className={`primary-btn ${loading ? "loading" : ""}`}
        disabled={loading}
      >
        {loading ? "Please wait..." : isRegister ? "Register" : "Login"}
      </button>
    </form>
  );
}

export default AuthForm;