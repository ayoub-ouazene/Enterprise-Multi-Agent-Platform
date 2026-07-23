import { RouterProvider } from 'react-router-dom';
import { QueryProvider } from './app/providers/QueryProvider';
import { AuthProvider } from './app/providers/AuthProvider';
import { SseProvider } from './app/providers/SseProvider';
import { router } from './app/router';

export default function App() {
  return (
    <QueryProvider>
      <AuthProvider>
        <SseProvider>
          <RouterProvider router={router} />
        </SseProvider>
      </AuthProvider>
    </QueryProvider>
  );
}
