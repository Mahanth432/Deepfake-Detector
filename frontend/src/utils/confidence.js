export function getDisplayConfidence(prediction, rawScore) {
  const score = Number(rawScore ?? 0);
  return score * 100;
}
