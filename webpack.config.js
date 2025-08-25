const path = require("path");
const BundleTracker = require('webpack-bundle-tracker');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';
  
  return {
    entry: {
      scheduleApp: './assets/js/schedule-app/index.js',
    },
    output: {
      path: path.resolve('./static/bundles/'),
      filename: "[name]-[hash].js",
      publicPath: '/scheduler/static/bundles/',
      clean: true,
    },
    devtool: isProduction ? false : 'eval-cheap-module-source-map',
    module: {
      rules: [
        {
          test: /\.js$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
            options: {
              presets: ['@babel/preset-env', '@babel/preset-react']
            }
          },
        },
        {
          test: /\.css$/,
          use: ['style-loader', 'css-loader'],
        },
      ],
    },
    plugins: [
      new BundleTracker({filename: './webpack-stats.json'}),
    ],
  };
};