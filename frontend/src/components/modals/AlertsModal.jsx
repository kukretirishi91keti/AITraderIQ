import React from 'react';

const AlertsModal = ({
  onClose,
  alerts,
  newAlertPrice,
  setNewAlertPrice,
  newAlertCondition,
  setNewAlertCondition,
  onAddAlert,
  onRemoveAlert,
}) => (
  <div
    className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
    onClick={onClose}
  >
    <div className="bg-gray-800 rounded-lg max-w-md w-full" onClick={(e) => e.stopPropagation()}>
      <div className="p-4 border-b border-gray-700 flex justify-between items-center">
        <h2 className="text-xl font-bold text-orange-400">🔔 Price Alerts</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">
          &times;
        </button>
      </div>
      <div className="p-4">
        <div className="flex gap-2 mb-4">
          <input
            type="number"
            value={newAlertPrice}
            onChange={(e) => setNewAlertPrice(e.target.value)}
            placeholder="Price"
            className="flex-1 bg-gray-700 px-3 py-2 rounded text-sm"
          />
          <select
            value={newAlertCondition}
            onChange={(e) => setNewAlertCondition(e.target.value)}
            className="bg-gray-700 px-3 py-2 rounded text-sm"
          >
            <option value="above">Above</option>
            <option value="below">Below</option>
          </select>
          <button
            onClick={onAddAlert}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-sm font-medium"
          >
            Add
          </button>
        </div>

        <div className="space-y-2">
          {alerts.length === 0 ? (
            <p className="text-gray-400 text-center py-4">No alerts set</p>
          ) : (
            alerts.map((alert, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-gray-700/50 rounded">
                <span>
                  <span className="text-cyan-400 font-medium">{alert.symbol}</span>{' '}
                  {alert.condition} <span className="text-white">${alert.price}</span>
                </span>
                <button
                  onClick={() => onRemoveAlert(i)}
                  className="text-red-400 hover:text-red-300"
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  </div>
);

export default AlertsModal;
