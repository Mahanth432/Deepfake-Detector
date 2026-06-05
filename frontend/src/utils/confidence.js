export function getDisplayConfidence(prediction, rawScore) {
  const score = Number(rawScore ?? 0);
  if ((prediction || "").toLowerCase() === "real") {
    return (1 - score) * 100;
  }

  return score * 100;
}
