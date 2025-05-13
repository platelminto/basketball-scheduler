import React from 'react';

const AddGameButton = ({ onClick }) => {
  return (
    <button 
      type="button" 
      className="btn btn-sm btn-primary add-game-btn"
      onClick={onClick}
    >
      <i className="fas fa-plus"></i> Add Game
    </button>
  );
};

export default AddGameButton;