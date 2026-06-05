function Loader({ text = "Analyzing image..." }) {
  return (
    <div className="loader-wrap">
      <span className="loader" />
      <p>{text}</p>
    </div>
  );
}

export default Loader;
