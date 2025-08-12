import React, { useState, useEffect } from 'react';

const MultiSelectDropdown = ({ options, selectedValues, onChange, placeholder, allLabel = "All" }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest('[data-dropdown]')) {
        setIsOpen(false);
      }
    };
    
    if (isOpen) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [isOpen]);
  
  const handleOptionClick = (optionValue) => {
    if (optionValue === 'all') {
      onChange(['all']);
    } else {
      const newValues = selectedValues.includes('all') 
        ? [optionValue]
        : selectedValues.includes(optionValue)
          ? selectedValues.filter(val => val !== optionValue)
          : [...selectedValues.filter(val => val !== 'all'), optionValue];
      
      onChange(newValues.length === 0 ? ['all'] : newValues);
    }
  };

  const getDisplayText = () => {
    if (selectedValues.includes('all') || selectedValues.length === 0) {
      return allLabel;
    }
    if (selectedValues.length === 1) {
      const option = options.find(opt => opt.value === selectedValues[0]);
      return option ? option.label : selectedValues[0];
    }
    return `${selectedValues.length} selected`;
  };

  return (
    <div data-dropdown style={{ position: 'relative', minWidth: '140px' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: '8px 12px',
          border: '1px solid #ddd',
          borderRadius: '4px',
          background: 'white',
          cursor: 'pointer',
          fontSize: '14px',
          width: '100%',
          textAlign: 'left',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <span>{getDisplayText()}</span>
        <span style={{ marginLeft: '8px' }}>▼</span>
      </button>
      
      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          background: 'white',
          border: '1px solid #ddd',
          borderTop: 'none',
          borderRadius: '0 0 4px 4px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          zIndex: 1000,
          maxHeight: '200px',
          overflowY: 'auto'
        }}>
          <div
            onClick={() => handleOptionClick('all')}
            style={{
              padding: '8px 12px',
              cursor: 'pointer',
              backgroundColor: selectedValues.includes('all') ? '#f0f0f0' : 'transparent',
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <input
              type="checkbox"
              checked={selectedValues.includes('all')}
              readOnly
              style={{ marginRight: '8px' }}
            />
            {allLabel}
          </div>
          {options.map(option => (
            <div
              key={option.value}
              onClick={() => handleOptionClick(option.value)}
              style={{
                padding: '8px 12px',
                cursor: 'pointer',
                backgroundColor: selectedValues.includes(option.value) ? '#f0f0f0' : 'transparent',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <input
                type="checkbox"
                checked={selectedValues.includes(option.value)}
                readOnly
                style={{ marginRight: '8px' }}
              />
              {option.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MultiSelectDropdown;