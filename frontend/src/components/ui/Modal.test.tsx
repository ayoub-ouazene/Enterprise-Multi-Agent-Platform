import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { Modal } from './Modal';

function Subject() {
  const [open, setOpen] = useState(false);
  return <><button onClick={() => setOpen(true)}>Open dialog</button><Modal title="Confirm details" isOpen={open} onClose={() => setOpen(false)}><button>First action</button><button>Last action</button></Modal></>;
}

describe('dialog focus', () => {
  it('moves focus inside, traps tab, closes on escape, and restores focus', async () => {
    render(<Subject />);
    const trigger = screen.getByRole('button', { name: 'Open dialog' });
    trigger.focus();
    fireEvent.click(trigger);
    const first = await screen.findByRole('button', { name: 'Close' });
    await waitFor(() => expect(document.activeElement).toBe(first));
    const last = screen.getByRole('button', { name: 'Last action' });
    last.focus();
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(document.activeElement).toBe(first);
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });
});
