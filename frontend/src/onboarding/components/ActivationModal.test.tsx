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

  it('shows when open and disables confirm until typed', () => {
    render(
      <ActivationModal open={true} onClose={vi.fn()} onConfirm={vi.fn()} isActivating={false} />
    );
    expect(screen.queryByRole('dialog')).toBeTruthy();

    const confirmBtn = screen.getByRole('button', { name: /activate company/i }) as HTMLButtonElement;
    expect(confirmBtn.disabled).toBe(true);

    const input = screen.getByPlaceholderText('activate') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'wrong' } });
    expect(confirmBtn.disabled).toBe(true);

    fireEvent.change(input, { target: { value: 'activate' } });
    expect(confirmBtn.disabled).toBe(false);
  });

  it('calls onConfirm when clicked after typing', () => {
    const onConfirm = vi.fn();
    render(
      <ActivationModal open={true} onClose={vi.fn()} onConfirm={onConfirm} isActivating={false} />
    );

    fireEvent.change(screen.getByPlaceholderText('activate'), { target: { value: 'activate' } });
    fireEvent.click(screen.getByRole('button', { name: /activate company/i }));

    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
