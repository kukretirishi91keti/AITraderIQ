import React from 'react';
import { KEYBOARD_SHORTCUTS } from '../../constants/appConfig';

const KeyboardShortcutsModal = ({ onClose }) => (
  <div
    className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
    onClick={onClose}
  >
    <div className="bg-gray-800 rounded-lg max-w-md w-full" onClick={(e) => e.stopPropagation()}>
      <div className="p-4 border-b border-gray-700 flex justify-between items-center">
        <h2 className="text-xl font-bold text-cyan-400">⌨️ Keyboard Shortcuts</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">
          &times;
        </button>
      </div>

      <div className="p-4">
        <div className="space-y-3">
          {KEYBOARD_SHORTCUTS.map((shortcut) => (
            <div key={shortcut.key} className="flex items-center justify-between">
              <kbd className="px-3 py-1.5 bg-gray-700 rounded text-cyan-400 font-mono text-sm min-w-[60px] text-center">
                {shortcut.key}
              </kbd>
              <span className="text-gray-300 text-sm">{shortcut.description}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="p-4 border-t border-gray-700">
        <button
          onClick={onClose}
          className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-white font-medium"
        >
          Got it!
        </button>
      </div>
    </div>
  </div>
);

export default KeyboardShortcutsModal;
