import express from 'express';
import Event from './models/Event.js';
import { authMiddleware } from './middleware/auth.js';

const router = express.Router();

// GET /api/events  (public, optional filters)
router.get('/', async (req, res) => {
  try {
    const q = {};
    const { category, mode, tag } = req.query;
    if (category) q.category = category;
    if (mode) q.mode = mode;
    if (tag) q.tags = tag;
    const events = await Event.find(q).sort({ datetime: 1 }).lean();
    res.json(events);
  } catch (err) {
    res.status(500).json({ error: 'Could not fetch events' });
  }
});

// POST /api/events  (protected: organizer or admin)
router.post('/', authMiddleware, async (req, res) => {
  try {
    // for demo, any authenticated user can create events; enforce role in production
    const payload = req.body;
    payload.organizerId = req.user._id;
    if (payload.tags && typeof payload.tags === 'string') payload.tags = payload.tags.split(',').map(t => t.trim().toLowerCase());
    const ev = new Event(payload);
    await ev.save();
    res.status(201).json(ev);
  } catch (err) {
    res.status(500).json({ error: 'Failed to create event' });
  }
});

// GET /api/events/:id
router.get('/:id', async (req, res) => {
  try {
    const ev = await Event.findById(req.params.id).populate('organizerId','name email');
    if (!ev) return res.status(404).json({ error: 'Event not found' });
    res.json(ev);
  } catch (err) {
    res.status(500).json({ error: 'Could not fetch event' });
  }
});

// PUT /api/events/:id  (protected)
router.put('/:id', authMiddleware, async (req, res) => {
  try {
    const ev = await Event.findById(req.params.id);
    if (!ev) return res.status(404).json({ error: 'Event not found' });
    // optionally check ownership: if (!ev.organizerId.equals(req.user._id)) return res.status(403)
    Object.assign(ev, req.body);
    if (ev.tags && typeof ev.tags === 'string') ev.tags = ev.tags.split(',').map(t=>t.trim().toLowerCase());
    await ev.save();
    res.json(ev);
  } catch (err) {
    res.status(500).json({ error: 'Failed to update event' });
  }
});

// DELETE /api/events/:id (protected)
router.delete('/:id', authMiddleware, async (req, res) => {
  try {
    const ev = await Event.findById(req.params.id);
    if (!ev) return res.status(404).json({ error: 'Event not found' });
    await ev.remove();
    res.json({ message: 'Deleted' });
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete' });
  }
});

// POST /api/events/:id/rsvp (toggle)
router.post('/:id/rsvp', authMiddleware, async (req, res) => {
  try {
    const ev = await Event.findById(req.params.id);
    if (!ev) return res.status(404).json({ error: 'Event not found' });
    const userId = req.user._id;
    const idx = ev.rsvps.findIndex(id => id.equals(userId));
    let action;
    if (idx >= 0) {
      ev.rsvps.splice(idx,1); action = 'removed';
    } else {
      ev.rsvps.push(userId); action = 'added';
    }
    await ev.save();
    res.json({ message: `RSVP ${action}`, rsvps: ev.rsvps.length });
  } catch (err) {
    res.status(500).json({ error: 'Failed to toggle RSVP' });
  }
});

// GET /api/events/recommendations?userId=...
// Simple content-based scorer: overlap between user interests+skills and event tags
router.get('/recommendations/:userId', async (req, res) => {
  try {
    const userId = req.params.userId;
    const User = (await import('../models/User.js')).default;
    const user = await User.findById(userId);
    if (!user) return res.status(404).json({ error: 'User not found' });
    const events = await Event.find().lean();
    const interests = (user.interests || []).map(s=>s.toLowerCase());
    const skills = (user.skills || []).map(s=>s.toLowerCase());
    function score(ev){
      const tags = (ev.tags||[]).map(t=>t.toLowerCase());
      let s = 0;
      interests.forEach(i => { if (tags.includes(i)) s += 2; });
      skills.forEach(sk => { if (tags.includes(sk)) s += 1; });
      return s;
    }
    const scored = events.map(e=> ({...e, score: score(e)}));
    scored.sort((a,b)=> b.score - a.score || new Date(a.datetime) - new Date(b.datetime));
    res.json(scored.slice(0,20));
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Recommendations error' });
  }
});

export default router;
