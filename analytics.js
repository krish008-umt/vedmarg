import express from 'express';
import Event from './models/Event.js';
const router = express.Router();

// GET /api/analytics
router.get('/', async (req, res) => {
  try {
    const totalEvents = await Event.countDocuments();
    const all = await Event.find().lean();
    const byCategory = {};
    all.forEach(e => { byCategory[e.category] = (byCategory[e.category]||0) + 1; });
    res.json({ totalEvents, byCategory });
  } catch (err) {
    res.status(500).json({ error: 'Analytics error' });
  }
});

export default router;
