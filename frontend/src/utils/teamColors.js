const TEAM_COLOR_PALETTE = [
  { accent: '#1f6f78', surface: '#dff1f4', border: '#1f6f78' },
  { accent: '#8a6325', surface: '#f5ead9', border: '#8a6325' },
  { accent: '#3f7d4e', surface: '#e0f0e3', border: '#3f7d4e' },
  { accent: '#9a4d4d', surface: '#f5e0e0', border: '#9a4d4d' },
  { accent: '#3f6296', surface: '#e1e8f5', border: '#3f6296' },
  { accent: '#6a4f8f', surface: '#ebe2f5', border: '#6a4f8f' },
  { accent: '#7a6f2d', surface: '#f1edd7', border: '#7a6f2d' },
  { accent: '#2f7d74', surface: '#def2ef', border: '#2f7d74' },
  { accent: '#915d7b', surface: '#f3e3ec', border: '#915d7b' },
  { accent: '#4d6b52', surface: '#e4eee5', border: '#4d6b52' },
  { accent: '#8c4f3d', surface: '#f4e4df', border: '#8c4f3d' },
  { accent: '#4f5f87', surface: '#e5e9f3', border: '#4f5f87' },
  { accent: '#7c5e46', surface: '#f0e7e1', border: '#7c5e46' },
  { accent: '#4d7288', surface: '#e3edf2', border: '#4d7288' },
];

const DEFAULT_TEAM_COLOR = TEAM_COLOR_PALETTE[0];

export const buildTeamColorMap = (groups = []) => {
  const activeGroups = groups
    .filter((group) => group && group.id != null && group.name)
    .sort((left, right) => {
      if (left.id !== right.id) {
        return left.id - right.id;
      }

      return left.name.localeCompare(right.name, 'de');
    });

  const nextMap = {};

  activeGroups.forEach((group, index) => {
    nextMap[group.name] = TEAM_COLOR_PALETTE[index % TEAM_COLOR_PALETTE.length];
  });

  return nextMap;
};

export const getTeamColor = (teamName = '', teamColorMap = {}) => {
  return teamColorMap[teamName] || DEFAULT_TEAM_COLOR;
};
