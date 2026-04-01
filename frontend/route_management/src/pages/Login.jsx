import { useState } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Lock, Mail, ChevronRight} from 'lucide-react';
import { useLoginMutation } from '../features/auth/authApi';
import { setCredentials } from '../features/auth/authSlice';

const ROLE_ROUTES = {
  SUPER_ADMIN: '/admin/companies',
  COMPANY_ADMIN: '/company/dashboard',
  DRIVER: '/my-route',
};

const Login = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [login, { isLoading }] = useLoginMutation();

  const [form, setForm] = useState({ email: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const data = await login(form).unwrap();
      dispatch(setCredentials(data));
      navigate(ROLE_ROUTES[data.role] || '/');
    } catch (err) {
      setError(err?.data?.message || err?.data?.error?.details?.detail || '');
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#F8FAFC] font-sans p-6">
      
      

      <div className="w-full max-w-[460px] mt-12">
        {/* Main Content Card */}
        <div className="bg-white border border-slate-200 rounded-[1.25rem] shadow-sm overflow-hidden">
          
          <div className="p-8 border-b border-slate-100 bg-slate-50/50">
            <h1 className="text-2xl font-bold text-slate-900">Welcome Back</h1>
            <p className="text-slate-500 text-sm mt-1">Please enter your administrative credentials</p>
          </div>

          <div className="p-8">
            {error && (
              <div className="mb-6 flex items-center gap-3 text-sm font-medium text-rose-600 bg-rose-50 border border-rose-100 p-4 rounded-xl">
                <div className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
                {error}
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-6">
              {/* Email Field */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-700 ml-0.5">
                  Email Address
                </label>
                <div className="relative group">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-600 transition-colors" size={18} />
                  <input
                    name="email"
                    type="email"
                    required
                    value={form.email}
                    onChange={handleChange}
                    placeholder="name@company.com"
                    className="w-full bg-white border border-slate-200 rounded-xl pl-12 pr-4 py-3 text-slate-900 text-sm focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all placeholder:text-slate-400"
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-semibold text-slate-700 ml-0.5">
                    Security Password
                  </label>
                  <button type="button" className="text-xs font-bold text-blue-600 hover:text-blue-700 transition-colors">
                    Forgot?
                  </button>
                </div>
                <div className="relative group">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-600 transition-colors" size={18} />
                  <input
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={form.password}
                    onChange={handleChange}
                    placeholder="••••••••"
                    className="w-full bg-white border border-slate-200 rounded-xl pl-12 pr-12 py-3 text-slate-900 text-sm focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(prev => !prev)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3.5 rounded-xl font-bold text-sm shadow-md shadow-blue-500/20 active:scale-[0.98] transition-all disabled:opacity-70 flex justify-center items-center gap-2 group"
                >
                  {isLoading ? (
                    <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      Sign In to Platform
                      <ChevronRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
        <footer className="mt-8 text-center">
          <p className="text-[10px] text-slate-400 font-medium">
            &copy; RouteMaster 2026 All rights reserved.
          </p>
        </footer>
      </div>
    </div>
  );
};

export default Login;
