import React from 'react';
import { createRoot } from 'react-dom/client';
import { AttioApp } from '@attio/sdk';
import QuoteWidget from './components/QuoteWidget';

// Initialize Attio App
const app = new AttioApp();

// Register widget
app.registerWidget('quote-widget', QuoteWidget);

// Register save quote handler (server-side route)
app.registerRoute('/save-quote', async (request, context) => {
  const { quoteResults, recordId } = request.body;
  
  try {
    // Use Attio SDK to assert/upsert record
    const record = await context.attio.records.assert({
      object: 'quote',
      matching_attribute: 'record_id',
      values: {
        record_id: recordId,
        total_cost: quoteResults.total_cost,
        contract_size: quoteResults.contract_size,
        allocations: JSON.stringify(quoteResults.allocations),
        quote_date: new Date().toISOString(),
      }
    });
    
    return {
      success: true,
      record: record
    };
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
});

// Export the app
export default app;
