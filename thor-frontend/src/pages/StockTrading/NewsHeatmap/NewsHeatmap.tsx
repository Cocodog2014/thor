import { Paper, Typography, Box } from '@mui/material';

const NewsHeatmap = () => {
  return (
    <Paper elevation={0} className="news-heatmap-panel">
      <Box className="news-heatmap-header">
        <Typography variant="h5" className="news-heatmap-title">
          News & Heatmap
        </Typography>
        <Typography variant="body2" className="news-heatmap-subtitle">
          Sector movers and headlines
        </Typography>
      </Box>
      <Box className="news-heatmap-placeholder">
        <Typography variant="body2">
          Visualization modules coming soon.
        </Typography>
      </Box>
    </Paper>
  );
};

export default NewsHeatmap;
