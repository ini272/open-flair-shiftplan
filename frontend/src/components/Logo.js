import React from 'react';

const Logo = ({ 
  size = 'medium', 
  style = {}, 
  onClick = null,
  ...props 
}) => {
  const sizes = {
    small: '30px',
    medium: '50px', 
    large: '80px',
    header: '40px'
  };

  const logoStyle = {
    maxHeight: sizes[size],
    width: 'auto',
    objectFit: 'contain',
    cursor: onClick ? 'pointer' : 'default',
    ...style // Allow custom styles to override
  };

  return (
    <img 
      src="/open-flair-logo.png"
      alt="Open Flair Logo" 
      style={logoStyle}
      onClick={onClick}
      {...props}
    />
  );
};

export default Logo;