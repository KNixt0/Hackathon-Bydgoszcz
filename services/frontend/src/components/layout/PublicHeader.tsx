import { Link } from "react-router-dom";

/** Row 1 of the header only (service name and tagline): used on pages without a session. */
export function PublicHeader({ linkTo }: { linkTo?: string }) {
  const inner = (
    <>
      <span className="hd__name">WatchIT</span>
    </>
  );
  return (
    <header className="hd hd--public">
      <div className="hd__top">
        {linkTo ? <Link to={linkTo} className="hd__svc">{inner}</Link> : <span className="hd__svc">{inner}</span>}
      </div>
    </header>
  );
}
