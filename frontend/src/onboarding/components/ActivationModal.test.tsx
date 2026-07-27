import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ActivationModal } from './ActivationModal';

describe('ActivationModal', () => {
  it('is hidden when not open', () => {
    const { container } = render(
      <ActivationModal open={false} onClose={vi.fn()} onConfirm={vi.fn()} isActivating={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows when open and disables confirm until acknowledged', () => {
    render(
      <ActivationModal open={true} onClose={vi.fn()} onConfirm={vi.fn()} isActivating={false} />
    );
    expect(screen.queryByRole('dialog')).toBeTruthy();

    const confirmBtn = screen.getByRole('button', { name: /activate company/i }) as HTMLButtonElement;
    expect(confirmBtn.disabled).toBe(true);

    fireEvent.click(screen.getByRole('checkbox'));
    expect(confirmBtn.disabled).toBe(false);
  });

  it('calls onConfirm when clicked after acknowledgement', () => {
    const onConfirm = vi.fn();
    render(
      <ActivationModal open={true} onClose={vi.fn()} onConfirm={onConfirm} isActivating={false} />
    );

    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /activate company/i }));

    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
