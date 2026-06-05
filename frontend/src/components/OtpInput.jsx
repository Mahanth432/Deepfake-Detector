import { useEffect, useRef } from "react";

function OtpInput({ value, onChange, disabled }) {
  const inputsRef = useRef([]);
  const digits = Array.from({ length: 6 }, (_, index) => value?.[index] || "");

  useEffect(() => {
    if (inputsRef.current[0] && value.length === 0) {
      inputsRef.current[0].focus();
    }
  }, [value]);

  const handleChange = (index, event) => {
    const nextValue = event.target.value.replace(/\D/g, "").slice(0, 1);
    const newDigits = [...digits];
    newDigits[index] = nextValue;
    const newOtp = newDigits.join("");
    onChange(newOtp);

    if (nextValue && index < inputsRef.current.length - 1) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, event) => {
    if (event.key === "Backspace" && !digits[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  return (
    <div className="otp-input-row">
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(element) => (inputsRef.current[index] = element)}
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          pattern="[0-9]*"
          maxLength={1}
          value={digit}
          onChange={(event) => handleChange(index, event)}
          onKeyDown={(event) => handleKeyDown(index, event)}
          disabled={disabled}
          className="otp-digit-input"
        />
      ))}
    </div>
  );
}

export default OtpInput;
