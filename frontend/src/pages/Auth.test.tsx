import{render,screen}from'@testing-library/react';import userEvent from'@testing-library/user-event';import{describe,expect,it,vi}from'vitest';import{Auth}from'./Auth';
describe('Auth',()=>{it('switches to a validated registration form',async()=>{render(<Auth onAuth={vi.fn()}/>);await userEvent.click(screen.getByRole('button',{name:/create an account/i}));expect(screen.getByRole('heading',{name:/create your workspace/i})).toBeInTheDocument();expect(screen.getByLabelText(/full name/i)).toBeRequired();expect(screen.getByLabelText(/password/i)).toHaveAttribute('minlength','10')})})

