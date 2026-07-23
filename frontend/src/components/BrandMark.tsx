export function BrandMark(): React.JSX.Element {
  return (
    <span className="brand" aria-label="GapSense">
      <svg className="brand__mark" viewBox="0 0 40 40" aria-hidden="true">
        <path d="M8 8h10v10H8z" />
        <path d="M22 8h10v10H22z" />
        <path d="M8 22h10v10H8z" />
        <path className="brand__mark-gap" d="M22 22h10v10H22z" />
      </svg>
      <span className="brand__word">GapSense</span>
    </span>
  );
}
