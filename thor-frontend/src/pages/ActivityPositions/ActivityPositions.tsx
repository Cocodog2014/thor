const ActivityPositions = () => {
  return (
    <div className="activity-positions-container">
      <h2 className="activity-positions-title">Trading Activity & Positions</h2>
      
      {/* Today's Trade Activity */}
      <section className="trade-activity-section">
        <h3 className="section-title">Today's Trade Activity</h3>
        
        {/* Working Orders */}
        <div className="activity-group">
          <h4 className="activity-header">Working Orders: 0</h4>
          <div className="activity-empty">No active orders</div>
        </div>

        {/* Filled Orders */}
        <div className="activity-group">
          <h4 className="activity-header">Filled Orders: 0</h4>
          <div className="activity-empty">No filled orders today</div>
        </div>

        {/* Cancelled Orders */}
        <div className="activity-group">
          <h4 className="activity-header">Cancelled Orders: 1 order</h4>
          <div className="cancelled-order">
            <div className="order-header">
              <span className="order-type">FUTURE</span>
              <span className="order-action">+1 TO OPEN</span>
            </div>
            <div className="order-details">
              <span className="order-symbol">/YM Z25</span>
              <span className="order-info">MKT - DAY</span>
            </div>
            <div className="order-status">REJECTED: You do not have...</div>
          </div>
        </div>
      </section>

      {/* Rolling Strategies */}
      <section className="strategies-section">
        <h3 className="section-title">Rolling Strategies: 0</h3>
        <div className="strategies-empty">No rolling strategies</div>
      </section>

      {/* Position Statement */}
      <section className="positions-section">
        <h3 className="section-title">Position Statement</h3>
        
        {/* Position Controls */}
        <div className="position-controls">
          <label className="control-item">
            <input type="checkbox" defaultChecked />
            Beta Weighting
          </label>
          <span className="weight-status">NOT WEIGHTED</span>
        </div>

        {/* Positions Table */}
        <div className="positions-table-container">
          <table className="positions-table">
            <thead>
              <tr>
                <th>Instrument</th>
                <th>Qty</th>
                <th>Days</th>
                <th>Trade Price</th>
                <th>Mark</th>
                <th>Net Liq</th>
                <th>% Change</th>
                <th>P/L %</th>
                <th>P/L Open</th>
                <th>P/L Day</th>
                <th>BP Effect</th>
              </tr>
            </thead>
            <tbody>
              <tr className="position-row">
                <td className="instrument-cell">YFF</td>
                <td className="qty-positive">+901</td>
                <td>3.7114</td>
                <td>8508</td>
                <td>3.25</td>
                <td className="amount-positive">$1,279.42</td>
                <td className="percent-negative">-16.97%</td>
                <td className="percent-negative">-61.82%</td>
                <td className="amount-negative">($2,072.02)</td>
                <td className="amount-positive">$45.05</td>
                <td className="amount-neutral">$0.00</td>
              </tr>
              <tr className="position-row">
                <td className="instrument-cell">VFF</td>
                <td className="qty-positive">+26,000</td>
                <td>-.06</td>
                <td>-</td>
                <td>-</td>
                <td className="amount-positive">$84,500.00</td>
                <td className="percent-negative">-9.32%</td>
                <td className="percent-positive">+282.01%</td>
                <td className="amount-positive">$62,380.20</td>
                <td className="amount-negative">($1,560.00)</td>
                <td className="amount-neutral">$0.00</td>
              </tr>
            </tbody>
          </table>
          
          {/* Subtotals */}
          <div className="position-subtotals">
            <div className="subtotal-row">
              <span className="subtotal-label">Subtotals</span>
              <span className="subtotal-amount">$85,779.42</span>
              <span className="subtotal-percent">+236.77%</span>
              <span className="subtotal-amount">$60,308.18</span>
              <span className="subtotal-amount negative">($1,514.95)</span>
              <span className="subtotal-amount">$0.00</span>
            </div>
            <div className="total-row">
              <span className="total-label">Overall Totals</span>
              <span className="total-amount">$60,308.18</span>
              <span className="total-amount negative">($1,514.95)</span>
              <span className="total-amount">$0.00</span>
            </div>
          </div>
        </div>
      </section>

      {/* Account Status */}
      <div className="account-status">
        <span className="status-label">ACCOUNT STATUS:</span>
        <span className="status-value ok">OK TO TRADE</span>
      </div>
    </div>
  );
};

export default ActivityPositions;