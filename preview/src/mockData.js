export const APP_NAME = 'TaskDown';
export const APP_ICON = '⚡';

export const currentParent = {
  id: 1, username: 'markiimark', first_name: 'Mark', is_parent: true, avatar_color: '#6C63FF',
};

export const currentKid = {
  id: 2, username: 'eva_2014', first_name: 'Eva', is_kid: true, points: 74, avatar_color: '#F7557A',
};

export const kids = [
  { id: 2, first_name: 'Eva',   points: 74,  avatar_color: '#F7557A', pending: 2, completed: 8 },
  { id: 3, first_name: 'Nora',  points: 55,  avatar_color: '#FF9800', pending: 3, completed: 5 },
  { id: 4, first_name: 'Marco', points: 102, avatar_color: '#4CAF50', pending: 1, completed: 12 },
];

export const tasks = [
  { id: 1, title: 'Clean your room',      category: 'chores',   priority: 3, points_value: 15, completed: false, assigned_to: 'Eva',   due_date: '2026-04-27T18:00' },
  { id: 2, title: 'Do homework',           category: 'homework', priority: 4, points_value: 20, completed: false, assigned_to: 'Nora',  due_date: '2026-04-26T16:00' },
  { id: 3, title: 'Brush teeth (morning)', category: 'hygiene',  priority: 2, points_value: 5,  completed: true,  assigned_to: 'Marco', due_date: '2026-04-26T08:00', completed_at: '2026-04-26T08:15', fun_rating: 'Okay' },
  { id: 4, title: 'Take out trash',        category: 'chores',   priority: 2, points_value: 10, completed: false, assigned_to: 'Eva',   due_date: '2026-04-26T19:00' },
  { id: 5, title: 'Read for 20 mins',      category: 'homework', priority: 2, points_value: 10, completed: true,  assigned_to: 'Nora',  due_date: '2026-04-26T21:00', completed_at: '2026-04-26T20:30', fun_rating: 'Fun' },
];

export const rewards = [
  { id: 1, title: 'Extra screen time', icon: '📱', points_cost: 30,  description: '1 extra hour' },
  { id: 2, title: 'Movie night pick',  icon: '🎬', points_cost: 50,  description: 'You choose the movie' },
  { id: 3, title: 'Ice cream',         icon: '🍦', points_cost: 25,  description: 'Trip to the ice cream shop' },
  { id: 4, title: 'Stay up late',      icon: '🌙', points_cost: 40,  description: '1 hour past bedtime' },
  { id: 5, title: 'Pizza night',       icon: '🍕', points_cost: 75,  description: 'Pick the toppings' },
  { id: 6, title: 'Game time',         icon: '🎮', points_cost: 35,  description: '30 extra mins gaming' },
];

export const redemptions = [
  { id: 1, kid: 'Eva',  reward: 'Extra screen time', icon: '📱', points_cost: 30, status: 'pending',  requested_at: '2 hours ago' },
  { id: 2, kid: 'Marco', reward: 'Pizza night',      icon: '🍕', points_cost: 75, status: 'approved', requested_at: 'Yesterday', resolved_at: 'Yesterday' },
];

export const transactions = [
  { id: 1, amount: +15, description: 'Completed: Clean your room',  type: 'task',              time: '2h ago' },
  { id: 2, amount: +5,  description: 'Completed: Brush teeth',       type: 'task',              time: 'Today' },
  { id: 3, amount: -10, description: 'Arguing at dinner',            type: 'behavior_negative', time: 'Yesterday' },
  { id: 4, amount: +20, description: 'Positive: Helped a sibling',   type: 'behavior_positive', time: '2 days ago' },
  { id: 5, amount: -30, description: 'Redeemed: Extra screen time',  type: 'redemption',        time: '3 days ago' },
];

export const behaviors = [
  { id: 1, kid: 'Eva',   type: 'positive', description: 'Helped set the table without being asked', points: 10, time: 'Today, 6:30 PM' },
  { id: 2, kid: 'Marco', type: 'negative', description: 'Arguing at dinner',                        points: 10, time: 'Yesterday, 7:00 PM' },
  { id: 3, kid: 'Nora',  type: 'positive', description: 'Finished homework early',                  points: 15, time: '2 days ago' },
];
