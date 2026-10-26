import { Link } from 'react-router-dom';

interface LogoProps {
  size?: 'default' | 'large';
}

export function Logo({ size = 'default' }: LogoProps) {
  const isLarge = size === 'large';

  return (
    <Link to="/" className="inline-flex items-baseline gap-2 no-underline">
      <span
        className={`
          font-bold tracking-tight text-gray-900
          ${isLarge ? 'text-4xl' : 'text-xl'}
        `}
      >
        CYS
      </span>
      <span
        className={`
          text-gray-400 font-normal
          ${isLarge ? 'text-base' : 'text-xs'}
        `}
      >
        The Yard Archive
      </span>
    </Link>
  );
}
