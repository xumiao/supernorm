import React from 'react';
import PropTypes from 'prop-types';
import AceEditor from 'react-ace';
import 'brace/mode/sparql';
import 'brace/theme/tomorrow';
import 'brace/ext/language_tools';
import ace from 'brace';
import { areArraysShallowEqual } from '../../reduxUtils';

const langTools = ace.acequire('ace/ext/language_tools');

const keywords = (
  'import|namespace|delete|del' +
  'in|!in|max|min|ave|count|group|unique|sort|sample|' +
  '%python|%keras|%pytorch|' +
  'true|false|prob|tensor|label|tag|uid|timestamp|none|null|na'
);

const dataTypes = (
  'Integer|Datetime|String|Unicode|Float|Pattern|UUID|URL'
);

const sqlKeywords = [].concat(keywords.split('|'), dataTypes.split('|'));
export const sqlWords = sqlKeywords.map(s => ({
  name: s, value: s, score: 60, meta: 'norm-builtin',
}));

const propTypes = {
  actions: PropTypes.object.isRequired,
  onBlur: PropTypes.func,
  sql: PropTypes.string.isRequired,
  tables: PropTypes.array,
  queryEditor: PropTypes.object.isRequired,
  height: PropTypes.string,
  hotkeys: PropTypes.arrayOf(PropTypes.shape({
    key: PropTypes.string.isRequired,
    descr: PropTypes.string.isRequired,
    func: PropTypes.func.isRequired,
  })),
  onChange: PropTypes.func,
};

const defaultProps = {
  onBlur: () => {},
  onChange: () => {},
  tables: [],
};

class AceEditorWrapper extends React.PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      sql: props.sql,
      selectedText: '',
    };
    this.onChange = this.onChange.bind(this);
  }
  componentDidMount() {
    // Making sure no text is selected from previous mount
    this.props.actions.queryEditorSetSelectedText(this.props.queryEditor, null);
    this.setAutoCompleter(this.props);
  }
  componentWillReceiveProps(nextProps) {
    if (!areArraysShallowEqual(this.props.tables, nextProps.tables)) {
      this.setAutoCompleter(nextProps);
    }
    if (nextProps.sql !== this.props.sql) {
      this.setState({ sql: nextProps.sql });
    }
  }
  onBlur() {
    this.props.onBlur(this.state.sql);
  }
  onAltEnter() {
    this.props.onBlur(this.state.sql);
  }
  onEditorLoad(editor) {
    editor.commands.addCommand({
      name: 'runQuery',
      bindKey: { win: 'Alt-enter', mac: 'Alt-enter' },
      exec: () => {
        this.onAltEnter();
      },
    });
    this.props.hotkeys.forEach((keyConfig) => {
      editor.commands.addCommand({
        name: keyConfig.name,
        bindKey: { win: keyConfig.key, mac: keyConfig.key },
        exec: keyConfig.func,
      });
    });
    editor.$blockScrolling = Infinity; // eslint-disable-line no-param-reassign
    editor.selection.on('changeSelection', () => {
      const selectedText = editor.getSelectedText();
      // Backspace trigger 1 character selection, ignoring
      if (selectedText !== this.state.selectedText && selectedText.length !== 1) {
        this.setState({ selectedText });
        this.props.actions.queryEditorSetSelectedText(
          this.props.queryEditor, selectedText);
      }
    });
  }
  onChange(text) {
    this.setState({ sql: text });
    this.props.onChange(text);
  }
  getCompletions(aceEditor, session, pos, prefix, callback) {
    callback(null, this.state.words);
  }
  setAutoCompleter(props) {
    // Loading table and column names as auto-completable words
    let words = [];
    const columns = {};
    const tables = props.tables || [];
    tables.forEach((t) => {
      words.push({ name: t.name, value: t.name, score: 55, meta: 'table' });
      const cols = t.columns || [];
      cols.forEach((col) => {
        columns[col.name] = null;  // using an object as a unique set
      });
    });
    words = words.concat(Object.keys(columns).map(col => (
      { name: col, value: col, score: 50, meta: 'column' }
    )), sqlWords);

    this.setState({ words }, () => {
      const completer = {
        getCompletions: this.getCompletions.bind(this),
      };
      const normCompleter = {
          getCompletions: function(editor, session, pos, prefix, callback) {
              if (prefix.length === 0) { callback(null, []); return }
              $.getJSON('/sqllab/norm/autocomplete?prefix=' + prefix, function(wordList) {
                  callback(null, wordList.map(function(ea)  {
                      return {name: ea.word, value: ea.word, score: ea.score, meta: ea.meta}
                  }));
              })
          }
      };
      if (langTools) {
        langTools.setCompleters([completer, normCompleter]);
      }
    });
  }
  render() {
    return (
      <AceEditor
        mode="sparql"
        theme="tomorrow"
        onLoad={this.onEditorLoad.bind(this)}
        onBlur={this.onBlur.bind(this)}
        height={this.props.height}
        onChange={this.onChange}
        width="100%"
        editorProps={{ $blockScrolling: true }}
        enableLiveAutocompletion
        value={this.state.sql}
      />
    );
  }
}
AceEditorWrapper.defaultProps = defaultProps;
AceEditorWrapper.propTypes = propTypes;

export default AceEditorWrapper;
