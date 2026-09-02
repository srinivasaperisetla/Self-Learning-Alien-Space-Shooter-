import java.awt.*;

public class Label extends Rectangle{
	
	String str;
	int size;
	int xpos;
	int ypos;
	boolean tag;
	int score;
	
	public Label(String st, int s, int x, int y, boolean t) {
		str = st;
		size = s;
		xpos = x;
		ypos = y;
		tag = t;
	}
	
	public void draw(Graphics g) {
		g.setColor(Color.white);
		g.setFont(new Font("Consolas", Font.PLAIN, size));
		
		if(tag) {
			g.drawString(str+String.valueOf(score),xpos, ypos);
		}
		else {
			g.drawString(str,xpos, ypos);
		} 
	}
	
}
