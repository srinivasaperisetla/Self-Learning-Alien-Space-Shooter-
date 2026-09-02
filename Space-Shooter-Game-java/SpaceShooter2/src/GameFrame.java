import java.awt.*;
import javax.swing.*;
import java.util.*;
import java.awt.event.*;

public class GameFrame extends JFrame{
	
	GamePanel panel;
	
	public GameFrame() {
		panel = new GamePanel();
		add(panel);
		setResizable(false);
		setBackground(Color.black);
		setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
		pack();
		setLocationRelativeTo(null);
		setVisible(true);
	}

}
