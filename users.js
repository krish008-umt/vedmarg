import express from 'express';
import User from './models/User.js';
import { authMiddleware } from './middleware/auth.js';

const router = express.Router();

// GET profile (protected)
router.get('/me', authMiddleware, async (req, res) => {
  const user = await User.findById(req.user._id).select('-passwordHash');
  res.json({ user });
});

// PUT /api/users/me (update profile)
router.put('/me', authMiddleware, async (req, res) => {
  try {
    const updates = req.body;
    // allow updating: name, academic, skills, interests
    const allowed = ['name','academic','skills','interests'];
    allowed.forEach(k => { if (k in updates) req.user[k] = updates[k]; });
    await req.user.save();
    res.json({ user: req.user });
  } catch (err) {
    res.status(500).json({ error: 'Failed to update profile' });
  }
});

export default router;
