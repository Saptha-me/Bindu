#!/usr/bin/env node
const React = require('react');
const { render, Box, Text, useInput, useApp, Newline } = require('ink');
const axios = require('axios');
const meow = require('meow');
const importJsx = require('import-jsx');

// CLI Help
const cli = meow(`
	Usage
	  $ bindu-top [url]

	Options
	  --interval, -i  Refresh interval in ms (default: 2000)

	Examples
	  $ bindu-top
	  $ bindu-top http://localhost:4000
`, {
	importMeta: module,
	flags: {
		interval: {
			type: 'number',
			alias: 'i',
			default: 2000
		}
	}
});

const AGENT_URL = cli.input[0] || 'http://localhost:3773';
const REFRESH_MS = cli.flags.interval;

// UI Components
const App = () => {
	const { exit } = useApp();
	const [status, setStatus] = React.useState('Connecting...');
	const [tasks, setTasks] = React.useState([]);
	const [inputText, setInputText] = React.useState('');
	const [error, setError] = React.useState(null);

	// Fetch Tasks
	const fetchTasks = async () => {
		try {
			// Mocking task fetch for now since Bindu API docs are sparse on list-all endpoint
			// In real prod, we'd hit tasks/list or similar if available.
			// For now, let's just show connection status and last ping.
			const res = await axios.post(AGENT_URL, {
				jsonrpc: '2.0',
				method: 'health/check', // Assuming standard health check
				params: {},
				id: Date.now()
			}, { timeout: 1000 });
			
			setStatus('Online 🟢');
			setError(null);
		} catch (err) {
			setStatus('Offline 🔴');
			setError(err.message);
		}
	};

	// Polling
	React.useEffect(() => {
		fetchTasks();
		const timer = setInterval(fetchTasks, REFRESH_MS);
		return () => clearInterval(timer);
	}, []);

	// Handle Input
	useInput((input, key) => {
		if (key.return) {
			if (inputText.trim() === '/quit') {
				exit();
				return;
			}
			sendMessage(inputText);
			setInputText('');
		} else if (key.backspace || key.delete) {
			setInputText(prev => prev.slice(0, -1));
		} else {
			setInputText(prev => prev + input);
		}
	});

	const sendMessage = async (msg) => {
		try {
			const res = await axios.post(AGENT_URL, {
				jsonrpc: '2.0',
				method: 'message/send',
				params: {
					message: {
						role: 'user',
						parts: [{ kind: 'text', text: msg }],
						kind: 'message',
						messageId: `msg-${Date.now()}`,
						contextId: `ctx-${Date.now()}`,
						taskId: `task-${Date.now()}`
					}
				},
				id: Date.now()
			});
			
			// Add to local log
			setTasks(prev => [...prev, { 
				id: Date.now(), 
				role: 'user', 
				content: msg 
			}]);

			// If success, maybe fetch task status to get reply?
			// For now, just logging send success.
		} catch (err) {
			setError(`Send failed: ${err.message}`);
		}
	};

	return (
		<Box flexDirection="column" padding={1} borderStyle="round" borderColor="cyan" width={80}>
			<Box marginBottom={1}>
				<Text bold color="cyan">Bindu Top</Text>
				<Text> │ </Text>
				<Text color="gray">{AGENT_URL}</Text>
				<Text> │ </Text>
				<Text>{status}</Text>
			</Box>

			<Box flexDirection="column" height={15} borderStyle="single" borderColor="gray" paddingX={1}>
				{tasks.length === 0 ? (
					<Text color="gray">No recent tasks...</Text>
				) : (
					tasks.slice(-10).map(t => (
						<Box key={t.id}>
							<Text color={t.role === 'user' ? 'green' : 'blue'} bold>{t.role}: </Text>
							<Text>{t.content}</Text>
						</Box>
					))
				)}
			</Box>

			{error && <Text color="red">Error: {error}</Text>}

			<Box marginTop={1}>
				<Text bold color="green">❯ </Text>
				<Text>{inputText}</Text>
			</Box>
			
			<Box marginTop={1}>
				<Text color="gray" dimColor>Type message to chat • /quit to exit</Text>
			</Box>
		</Box>
	);
};

render(<App />);
