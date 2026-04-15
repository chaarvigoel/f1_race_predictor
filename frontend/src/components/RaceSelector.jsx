import RaceDropdown from './RaceDropdown.jsx';

/** Session keys must stay strings to match predictions.json and DOM values. */
export default function RaceSelector(props) {
  return <RaceDropdown {...props} />;
}
